# CDR MIM-aware parazitik çıkarım — 18 Ekim 2026

394 aygıtlı CDR layout'unda MIM cihaz maskelerinin korunması ve açık `cap_cmim` modeliyle çift sayımın önlenmesi için çıkarım akışı düzeltildi. Tam seri PHY, ana çip yönlendirmesi ve nihai zamanlama hâlâ açık.

## Fiziksel kaynak ve sorun

Kaynak, 560 DRC kuralını ve 394 aygıtlı hiyerarşik/düz LVS'yi geçen gerçek PD layout'udur. 122 HBT, 102 rppd, 11 MIM ve 159 sonlu ptap modeli içerir. İlk metal-only görünüm MIM/Vmim maskelerini dışarıda bıraktığı için MIM üzerindeki TM1–Metal5 örtüşmesini sıradan hat kapasitesi olarak hesaplıyordu.

Gerçek 3,6 / 4,8 / 40 µm PCell'ler üzerinde maskeli/maskesiz çıkarım karşılaştırıldı. MIM maskesi korununca, teknoloji dosyasındaki CDL cihaz-değeri tahmin katsayılarının ayrıca toprağa bağlı kapasite üretmesi de görüldü. Açık ngspice `cap_cmim` modeli bu cihaz kapasitesini zaten içeriyor.

Yalnız `defaultareacap *mimcap metal5 1500` ve `defaultperimeter *mimcap metal5 40` tahmin bildirimlerini kaldıran özel bir teknoloji kopyası kullanıldı. Diğer teknoloji dosyaları ve parazitik kurallar değişmedi. Bu kopyanın kapsamı, açık MIM alt devresi kullanılan `ngspice()` stilidir; CDL ve yalnız kapasite-değeri çıkarımı için onaylanmadı.

## Ölçülen farklar

| Kare MIM boyutu | Maskesiz ek plaka C | Maskeli ek plaka C | Tahmin açıkken PLUS–referans C | Açık model için düzeltilmiş PLUS–referans C |
|---|---:|---:|---:|---:|
| 3,6 µm | 0,597510 fF | 0,143658 fF | 19,800699 fF | 0,453193 fF |
| 4,8 µm | 1,091230 fF | 0,220565 fF | 35,101000 fF | 0,705464 fF |
| 40 µm | 70,009297 fF | 2,349720 fF | 2405,590000 fF | 17,008301 fF |

Tablo geometrik çıkarım sonuçlarını gösterir. Transient, PVT ve RF doğrulamaları ayrıca gerekiyor. Referans, çıkarıcının kapasite referansıdır; otomatik olarak bir besleme veya fiziksel substrat düğümüyle özdeşleştirilmez.

[Dokuz durumlu native karşılaştırma](https://github.com/Melihakbulut221/nssoc/actions/runs/39075539501) eski altı kontrolün sonuçlarını yeniden üretti; açık MIM modeli ve gerçek cihaz boyutları korundu. Tam kayıt: `docs/evidence/cdr-mim-explicit-model-pilot-pass-20261018.json`.

## Tam CDR sonucu

Tam layout'un metal/via geometrisi değişmeden MIM=36 ve Vmim=129 maskeleri eklendi. On bir alt plaka ölçüm noktası, MIM maskesinin dışındaki gerçek Metal5 erişimine taşındı. Bütün 776 nokta, native LVS ve bağımsız iletken grafiği üzerinden yeniden doğrulandı.

[Native tam CDR çıkarımı](https://github.com/Melihakbulut221/nssoc/actions/runs/39075921872) 8.956 direnç, 7.660 parazitik kapasite ve 11 açık `cap_cmim` kartı verdi. 111 fiziksel iletken bileşen korundu.

[Ham sonuç denetimi](https://github.com/Melihakbulut221/nssoc/actions/runs/39076409923) geçti: direnç değerleri/bağlantıları, her noktadaki toprak kapasitesi, karşılıklı kapasite bağlantıları/değerleri ve indirgenmiş kapasite matrisi eşleşti. Ham source/replacement ve iki SPICE görünümündeki 11 MIM kimliği, boyutu ve terminal sırası doğrulandı. 13 hat bozulması ve 9 MIM bozulması kontrolü reddedildi.

## Sonraki kabul kapıları

Yeni model birleştirmesi, 394 aygıtı ve bütün 16.616 hat elemanını korumalı; çıkarıcının 11 MIM kartını doğruladıktan sonra aynı cihazı ikinci kez eklememeli. Sonrasında yüklenmiş native PD transient testleri ve gerçek VCO geri beslemesi gerekiyor. Substrat yayılma direnci, RF dağılımı, süreç/köşe yeterliliği, tam PHY ve ana çip zamanlaması bu sonuçla kapanmış değildir.

Tüm işlemler GitHub-hosted ortamda çalıştırıldı. Eski sonuçlar ve başarısız denemeler korunuyor; yerel çalışma klasörü boş.
