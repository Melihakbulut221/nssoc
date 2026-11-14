# SRAM mühendislik LVS doğrulaması — 14 Kasım 2026

Çift portlu `RM_IHPSG13_2P_256x16_c2_bm_bist` makrosunun **mühendislik referansı ile tam makro LVS karşılaştırması geçti**. Bu sonuç özgün üretici CDL'sinin doğrulandığı veya tam çipin üretime hazır olduğu anlamına gelmez.

## Doğrulanan kapsam

- Özgün GDS değiştirilmedi; 70.110 ilkel eleman iki tarafta da korundu.
- 215 dış portun adları ve sayıları birebir doğrulandı; bağlantı ve boyut kontrolleri etkin kaldı.
- Karşılaştırılan 26 devrenin tamamı `Match`; çıkarım tanısı ve başarısız devre yok.
- `allow_unmatched_ports=false` korundu. Hücre içleri dışlanmadı, net eşanlamları veya eşdeğer pin istisnaları eklenmedi.
- Sonuç hem yerel KLayout karşılaştırma kararı hem bağımsız katı denetçi ile doğrulandı. Bütün CAD hesaplaması GitHub Actions üzerinde yapıldı.

## Sorunun çözümü

Yerleşim ve referansın SRAM blok/sütun/matris adları farklıydı. Açık hücre eşlemeleri, içeriklerini karşılaştırmaya devam ederek hiyerarşinin gereksiz açılmasını önledi. Farklı seviyelerde duran standart hücre sınırları iki tarafta aynı biçimde açıldı; eleman sayısı önce/sonra kontrol edildi.

Üst seviye pin oluşturma başlangıçta kapalıydı. İşlem hiyerarşi açıldıktan sonra etkinleştirilince 58 iç etiket dış port haline geldi; 215 port şartı bunu reddetti. Aracın kendi port oluşturma işlemi hiyerarşi açılmadan önceye taşındı. Hiçbir port elle silinmedi veya referansa göre seçilmedi.

Tanı amaçlı 16 dallanma sınırı yeterli değildi; kaydedilmiş karşılaştırma en az 360 gerektiren durumlar gösterdi. Sınır 512'ye çıkarıldığında, aynı kabul kurallarıyla tam karşılaştırma 13 saniyede geçti. Arama derinliği ve boyut toleransları gevşetilmedi.

## Tam makro hata kontrolleri

| Kontrol | Beklenen | Gerçek sonuç |
|---|---|---|
| Değiştirilmemiş mühendislik referansı | LVS geçer | 26 Match, katı denetim geçti |
| Bit hücresi R0 genişliği 0,2 µm → 0,3 µm | LVS reddeder | NoMatch, katı denetim reddetti |
| Bit hücresi R0 metal2 → metal3 | LVS reddeder | NoMatch, katı denetim reddetti |
| Bit hücresinde bir MOS gate bağlantısını koparma | LVS reddeder | NoMatch, katı denetim reddetti |

Dört kontrolde de gerçek yerel karşılaştırma tamamlandı. Altyapı hataları negatif test başarısı sayılmadı. Ek olarak 15 küçük devre kimlik/hata kontrolü her çalıştırmada uygulandı.

## Kanıtlar

- [İlk tam makro geçişi](https://github.com/Melihakbulut221/nssoc/actions/runs/43593043558), kaynak `cb15ee8f57f1050e8c1b7c6fc2a9e986bf7afa3b`.
- [Tam makro kimlik ve hata kontrolleri](https://github.com/Melihakbulut221/nssoc/actions/runs/43593348833), kaynak `411cb5d256664ff49086779b671cf347c3f60199`.
- Ayrıntılı hash, rapor ve kapsam kayıtları: `docs/evidence/dp-engineering-full-macro-pass-and-controls-20261114.json` ve `docs/evidence/dp-full-macro-controls-passed-20261114.json`.

## Açık kalan kapsam

Mühendislik CDL adayı sekiz direnç kaydında özgün üretici CDL'sinden farklıdır; üretici referansının resmî düzeltilmesi/kalifikasyonu tamamlanmadı. Tek portlu SRAM'in tam makro LVS'si, bu referansların çip hiyerarşisine entegrasyonu ve tam çip transistor LVS'si ayrıca doğrulanmalıdır. Bu çalışma SRAM Liberty/RC kalifikasyonu, nihai zamanlama, tam PCIe PHY veya üretici onayını kapatmaz.
