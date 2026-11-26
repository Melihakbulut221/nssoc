# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Run within KLayout batch mode with -rd db=... -rd top=...
require 'json'

raise 'Expected a database and top circuit' if $db.to_s.empty? || $top.to_s.empty?
# Reject an explicit native top mismatch before KLayout materializes all geometry.
# Every other outcome still goes through the complete native database checks.
def reject_explicit_top_failure(io, top)
  return unless io.gets(64) == "#%lvsdb-klayout\n"
  pair = /^ X\(#{Regexp.escape(top)} #{Regexp.escape(top)} [SX](?:[ )]|$)/i
  tail = ''.b
  comparison = false
  while (chunk = io.read(1 << 20))
    data = tail + chunk
    unless comparison
      start = data.index("\nZ(\n")
      if start
        comparison = true
        data = data.byteslice(start..)
      end
    end
    if comparison && data.match?(pair)
      raise 'Native comparison explicitly skipped or rejected the requested top'
    end
    tail = data.byteslice(-[data.bytesize, top.bytesize * 2 + 64].min..)
  end
end

File.open($db, 'rb') do |file|
  signature = file.read(2)
  file.rewind
  if signature == "\x1f\x8b".b
    require 'zlib'
    Zlib::GzipReader.wrap(file) { |stream| reject_explicit_top_failure(stream, $top) }
  elsif file.size >= (64 << 20)
    reject_explicit_top_failure(file, $top)
  end
end

report = RBA::LayoutVsSchematic.new
report.read($db)
raise 'Missing extracted or reference netlist' unless report.netlist && report.reference
counts = Hash.new(0)
matched_top = 0
report.xref.each_circuit_pair do |pair|
  status = pair.status.to_s
  counts[status] += 1
  if pair.first && pair.second
    if status == 'Match' && pair.first.name.casecmp?($top) && pair.second.name.casecmp?($top)
      report.xref.each_pin_pair(pair) do |pins|
        raise 'Unmatched top port' unless pins.first && pins.second && pins.status.to_s == 'Match'
        raise 'Top port name mismatch' unless pins.first.name.casecmp?(pins.second.name)
      end
      matched_top += 1
    end
  elsif status == 'Match'
    raise 'Matched circuit pair has a missing side'
  end
end
layout_roots = report.netlist.top_circuits.map(&:name)
reference_roots = report.reference.top_circuits.map(&:name)
puts JSON.generate(top: $top, layout_roots: layout_roots, reference_roots: reference_roots,
                   circuit_pair_counts: counts, matched_top_pairs: matched_top)
[layout_roots, reference_roots].each do |roots|
  raise 'Missing or ambiguous expected top circuit' unless roots.size == 1 && roots.first.casecmp?($top)
end
raise 'Incomplete or nonmatching circuit comparison' unless counts.keys == ['Match'] && matched_top == 1
