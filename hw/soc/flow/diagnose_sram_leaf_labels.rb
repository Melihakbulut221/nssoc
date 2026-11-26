# SPDX-License-Identifier: Apache-2.0
# Select one verified leaf and export a new diagnostic stream.
raise 'Use a new diagnostic output path' if File.exist?($out)
raise 'Unexpected mode' unless %w[original crossed].include?($mode)
raise 'Unknown leaf' unless %w[RSC_IHPSG13_WLDRVX8 RSC_IHPSG13_CINVX2].include?($leaf)
layout=RBA::Layout.new
layout.read($gds)
cell=layout.cell($leaf)
names=[]
cell.shapes(layout.layer(8,2)).each do |shape|
 next unless shape.is_text?
 t=shape.text.dup
 names << t.string
 t.string={'A'=>'Z','Z'=>'A'}.fetch(t.string,t.string) if $mode=='crossed'
 t.string=t.string.sub(/!$/,'')
 cell.shapes(layout.layer(8,25)).insert(t)
end
raise 'unexpected leaf labels' unless names.sort==%w[A VDD! VSS! Z]
cell.write($out)
