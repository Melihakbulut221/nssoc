# Tam CDR modeliyle yük altında doğrulama — 18 Ekim 2026

MIM-aware PD394 birleştirme koşusu [39076756076](https://github.com/Melihakbulut221/nssoc/actions/runs/39076756076) tamamlandı. Model, fiziksel tasarımdaki 122 HBT, 102 rppd, 11 MIM ve 159 gövde kontağını; ayrıca 8.956 direnç ve 7.660 parazitik kapasiteyi koruyor. On beş bozulmuş model kontrolü reddedildi. Bu sonuç elektriksel davranışın doğru olduğunu tek başına kanıtlamaz.

Yeni [39077465653 koşusu](https://github.com/Melihakbulut221/nssoc/actions/runs/39077465653), aynı modelde 256 özgün PRBS bitini erken ve geç veri geçişleriyle uygular. Saat durdurma ve V/I kutuplama akımını kesme deneyleri ayrıca çalışır. Önceki örnekleme, genlik, faz, akım ve transistor gerilim sınırları korunur. 26 port konum varsayımı yerine adlarıyla eşleştirilir; her gerçek HBT'nin akımı ve terminal gerilimleri ölçülür.

Örnekleyici başına her çıkışa eklenen 150 fF yük, LVS ve fiziksel referanslarla seçilen veri çiftinin gerçek kolektörüne bağlanır. Bu konum, ideal şematik çıkış düğümü veya makro sınırındaki pin ile özdeş kabul edilmez. Çıkış hattındaki tutma çiftinin kolektörü ve tüm dağıtılmış R/C ağı modelde kalır. Karşılaştırıcıların dış portlarında 50 fF yük bulunur. Bu açık konum tanımı, sonradan farklı noktalara bağlanan yüklerin aynı deneymiş gibi sunulmasını önler.

Bu deney harici 8 GHz saat kullanır. Kapalı çevrim CDR, VCO geri beslemesi, PVT ve zaman adımı yakınsaması, RF/substrat çıkarımı ve tam seri Gen3 x4 kabulü hâlâ gereklidir. İlk dalga sonuçları görülmeden bu başlıklar kapanmış sayılmaz.

Ana çipte [yerleştirme/CTS 39059854681](https://github.com/Melihakbulut221/nssoc/actions/runs/39059854681) tamamlandı. Kaynağı, 39059432529 koşusunda gerçek standart hücre ve SRAM modelleriyle önyükleme ve sistem/Ethernet MBIST kontrolünden geçen adaydır. PCIe bu önyükleme testinde boşta tutulur; trafik doğrulaması ayrı kanıttır. Yerleştirme özetindeki farklı aşamalardan devralınmış metrikler yeni bir nihai zamanlama sonucu değildir. Çalışan [39061293959](https://github.com/Melihakbulut221/nssoc/actions/runs/39061293959), bunları temizleyip aynı CTS veritabanında üç köşeyi ayrı süreçlerde ölçer, onarır ve yeniden ölçer. Ardından eşdeğerlik, yönlendirme ve çıkarılmış parazitiklerle nihai zamanlama gereklidir.

Kaynaklar ve sonuçlar yalnız GitHub'dadır. Yerel çalışma klasörü boş tutulur. Başarısız koşular ve kontrol sonuçları silinmez.
