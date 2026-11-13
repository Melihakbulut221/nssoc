# SPDX-License-Identifier: Apache-2.0
"""Make two implicit out-of-range memory X results explicit in the proof reference.
Product RTL remains untouched. No bounds assumption is introduced. Original
four-state HDL semantics: invalid/unknown unpacked-array index yields X; a
known valid index keeps its original value. Raw/normalized/candidate expressions
are independently checked before the normalized reference enters full proofs.
"""
RULES={
 'soc_pcie_lcrc_tx.v':("wire [7:0] cursor_data_byte=words[cursor_word] >> (8*cursor_byte);", "wire [7:0] cursor_data_byte=(32'(cursor_word)<MAX_TLP_DWORDS ? 8'(words[cursor_word] >> (8*cursor_byte)) : 8'hxx);"),
 'soc_pcie_rx_credit.v':("assign out_data_o=select_dllp ? dllp[output_index] : tlp_byte;", "assign out_data_o=select_dllp ? (32'(output_index)<6 ? dllp[output_index] : 8'hxx) : tlp_byte;")}
def normalize(name,text):
 if name not in RULES:return text
 old,new=RULES[name]
 assert text.count(old)==1,(name,'reference source differs')
 return text.replace(old,new)
