# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
# Run within KLayout batch mode with -rd db=... -rd top=...
require 'json'

raise 'Expected a database and top circuit' if $db.to_s.empty? || $top.to_s.empty?
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
