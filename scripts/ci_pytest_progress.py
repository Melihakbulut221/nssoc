# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Diagnostic-only pytest hooks: fsynced events and fail-closed partial JUnit.

No timeout, selection, skip, retry or report-outcome hook is installed.
The journal is authoritative during an interrupted test. Partial XML is a
separate diagnostic report; pytest's own JUnit remains untouched.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import xml.etree.ElementTree as ET

RECORDER = None


def atomic(path, raw):
    temporary = path.with_name(path.name + '.pending')
    with temporary.open('wb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def json_bytes(value):
    return (json.dumps(value, sort_keys=True, allow_nan=False) + '\n').encode()


def replay(rows):
    tests = []
    active = None
    finished = False
    exitstatus = None
    for expected, row in enumerate(rows, 1):
        if row.get('sequence') != expected:
            raise ValueError('complete sequential pytest journal')
        event = row['event']
        if event == 'COLLECTED':
            if tests:
                raise ValueError('single collected test census')
            tests = [{'ordinal': i, 'nodeid': nodeid, 'started': False, 'finished': False, 'reports': []}
                     for i, nodeid in enumerate(row['nodeids'])]
        elif event == 'TEST_START':
            if active is not None:
                raise ValueError('previous test must finish before next start')
            choices = [x for x in tests if x['nodeid'] == row['nodeid'] and not x['started']]
            if not choices:
                raise ValueError('started test belongs to actual collected census')
            active = choices[0]
            active['started'] = True
        elif event == 'TEST_REPORT':
            if active is None or active['nodeid'] != row['nodeid']:
                raise ValueError('report belongs to active test')
            active['reports'].append({k: row[k] for k in ('when', 'outcome', 'duration', 'longrepr')})
        elif event == 'TEST_FINISH':
            if active is None or active['nodeid'] != row['nodeid']:
                raise ValueError('finish belongs to active test')
            active['finished'] = True
            active = None
        elif event == 'SESSION_FINISH':
            finished = True
            exitstatus = row['exitstatus']
    return tests, active, finished, exitstatus


def xml_text(value):
    # The original text remains byte-exact in the JSONL journal. XML 1.0
    # cannot contain ANSI ESC/control/surrogate code points.
    return ''.join(ch if (ord(ch) in (9, 10, 13) or 32 <= ord(ch) <= 0xd7ff or 0xe000 <= ord(ch) <= 0xfffd or 0x10000 <= ord(ch) <= 0x10ffff) else '\\u%04x' % ord(ch) for ch in str(value))


def render(rows, out):
    tests, active, finished, exitstatus = replay(rows)
    counts = dict(tests=len(tests), failures=0, errors=0, skipped=0)
    suite = ET.Element('testsuite', name='nssoc-interruption-diagnostic',
                       session_finished=str(finished).lower(), authoritative_test_verdict='false')
    for test in tests:
        reports = test['reports']
        case = ET.SubElement(suite, 'testcase', name=xml_text(test['nodeid']),
                             ordinal=str(test['ordinal']), time=str(sum(x['duration'] for x in reports)))
        failures = [x for x in reports if x['outcome'] == 'failed']
        skips = [x for x in reports if x['outcome'] == 'skipped']
        if failures:
            for report in failures:
                tag = 'failure' if report['when'] == 'call' else 'error'
                counts['failures' if tag == 'failure' else 'errors'] += 1
                ET.SubElement(case, tag, type=report['when']).text = xml_text(report['longrepr'])
        elif not test['finished']:
            counts['errors'] += 1
            ET.SubElement(case, 'error', type='IncompleteTest').text = (
                'Started but not finished; see journal.' if test['started'] else
                'Collected but not executed before interruption; not a skipped or passing test.')
        elif skips:
            counts['skipped'] += 1
            ET.SubElement(case, 'skipped', type=skips[0]['when']).text = xml_text(skips[0]['longrepr'])
        elif not any(x['when'] == 'call' and x['outcome'] == 'passed' for x in reports):
            counts['errors'] += 1
            ET.SubElement(case, 'error', type='IncompleteReports').text = 'No completed passing call or explicit skip.'
    for key, value in counts.items():
        suite.set(key, str(value))
    atomic(out / 'partial-junit.xml', ET.tostring(suite, encoding='utf-8', xml_declaration=True))
    state = {'schema': 'nssoc-pytest-progress-v1', 'journal_records': len(rows),
             'collected': len(tests), 'started': sum(x['started'] for x in tests),
             'finished': sum(x['finished'] for x in tests),
             'active': None if active is None else {'ordinal': active['ordinal'], 'nodeid': active['nodeid']},
             'session_finished': finished, 'pytest_exitstatus': exitstatus,
             'all_collected_finished': bool(finished and all(x['finished'] for x in tests)),
             'diagnostic_only': True, 'partial_junit_counts': counts}
    atomic(out / 'progress.json', json_bytes(state))
    return state


def read_journal(path):
    raw = path.read_bytes()
    if raw and not raw.endswith(b'\n'):
        raise ValueError('partial final pytest journal record; original bytes retained')
    return [json.loads(line) for line in raw.splitlines()]


def finalize(out):
    out = Path(out)
    rows = read_journal(out / 'events.jsonl')
    state = render(rows, out)
    state['events_sha256'] = hashlib.sha256((out / 'events.jsonl').read_bytes()).hexdigest()
    return state


class Recorder:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=False)
        self.stream = (self.out / 'events.jsonl').open('x', encoding='utf-8')
        self.rows = []
        self.last_render = 0.0

    def event(self, kind, **fields):
        row = {'sequence': len(self.rows) + 1, 'event': kind,
               'monotonic_ns': time.monotonic_ns(), **fields}
        raw = json_bytes(row)
        self.stream.write(raw.decode('utf-8'))
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.rows.append(row)
        # Each event is immediately durable. Full partial XML is periodically
        # rebuilt to avoid rewriting all test records for every phase.
        if time.monotonic() - self.last_render >= 10 or kind in ('COLLECTED', 'SESSION_FINISH', 'INTERRUPTED', 'INTERNAL_ERROR'):
            render(self.rows, self.out)
            self.last_render = time.monotonic()
        if kind in ('TEST_START', 'TEST_FINISH', 'INTERRUPTED', 'INTERNAL_ERROR'):
            message = '[pytest-progress] ' + json.dumps(row, sort_keys=True) + '\n'
            os.write(2, message.encode('utf-8'))


def pytest_sessionstart(session):
    global RECORDER
    output = os.environ.get('NSSOC_PYTEST_PROGRESS')
    if not output:
        raise RuntimeError('explicit owned pytest progress directory required')
    RECORDER = Recorder(output)
    RECORDER.event('SESSION_START', source=os.environ.get('GITHUB_SHA'),
                   run=os.environ.get('GITHUB_RUN_ID'), attempt=os.environ.get('GITHUB_RUN_ATTEMPT'))


def pytest_collection_finish(session):
    RECORDER.event('COLLECTED', nodeids=[item.nodeid for item in session.items])


def pytest_runtest_logstart(nodeid, location):
    RECORDER.event('TEST_START', nodeid=nodeid)


def pytest_runtest_logreport(report):
    RECORDER.event('TEST_REPORT', nodeid=report.nodeid, when=report.when,
                   outcome=report.outcome, duration=report.duration, longrepr=str(report.longrepr or ''))


def pytest_runtest_logfinish(nodeid, location):
    RECORDER.event('TEST_FINISH', nodeid=nodeid)


def pytest_keyboard_interrupt(excinfo):
    if RECORDER is not None:
        RECORDER.event('INTERRUPTED', detail=str(excinfo))


def pytest_internalerror(excrepr, excinfo):
    if RECORDER is not None:
        RECORDER.event('INTERNAL_ERROR', detail=str(excrepr))


def pytest_sessionfinish(session, exitstatus):
    if RECORDER is not None:
        RECORDER.event('SESSION_FINISH', exitstatus=int(exitstatus))
        RECORDER.stream.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--finalize', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(finalize(args.finalize), sort_keys=True))
