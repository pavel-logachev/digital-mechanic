'use strict';

// Each row is a complete UI string, in the same order as languages below.
// Keep variables in braces so each language can put them in the right place.
const mechanicI18n = (() => {
  const languages = Object.freeze({ru: 'Русский', uz: 'O‘zbekcha', tg: 'Тоҷикӣ', ky: 'Кыргызча', kk: 'Қазақша', hi: 'हिन्दी', en: 'English'});
  const rows = `
brand|Цифровой механик|Raqamli mexanik|Механики рақамӣ|Санарип механик|Цифрлық механик|डिजिटल मैकेनिक|Digital Mechanic
language|Язык|Til|Забон|Тил|Тіл|भाषा|Language
large|Крупный шрифт|Yirik yozuv|Ҳарфи калон|Чоң арип|Ірі қаріп|बड़े अक्षर|Large text
back|Назад|Orqaga|Бозгашт|Артка|Артқа|वापस|Back
demo|Демо|Demo|Намоиш|Демо|Демо|डेमो|Demo
fleet|Сводка парка для главного механика|Bosh mexanik uchun park holati|Ҳолати парк барои механики калон|Башкы механик үчүн парктын абалы|Бас механикке арналған парк жағдайы|मुख्य मैकेनिक के लिए पार्क सारांश|Fleet overview for the chief mechanic
vehicle|Карточка машины|Mashina kartasi|Маълумоти мошин|Унаа тууралуу|Көлік картасы|गाड़ी की जानकारी|Vehicle details
chat|Диагностика|Diagnostika|Ташхис|Диагностика|Диагностика|जाँच का नतीजा|Diagnosis
draft|Черновик заявки|Buyurtma qoralamasi|Пешнависи дархост|Өтүнмөнүн долбоору|Өтінім жобасы|वर्क ऑर्डर का मसौदा|Work order draft
receipt|Заявка создана|Buyurtma ochildi|Дархост сабт шуд|Өтүнмө түзүлдү|Өтінім жасалды|वर्क ऑर्डर बन गया|Work order created
choose|Выберите машину|Mashinani tanlang|Мошинро интихоб кунед|Унааны тандаңыз|Көлікті таңдаңыз|गाड़ी चुनें|Choose a vehicle
search|Госномер или гаражный номер|Davlat yoki garaj raqami|Рақами давлатӣ ё гаражӣ|Мамлекеттик же гараж номери|Мемлекеттік не гараж нөмірі|रजिस्ट्रेशन या गैराज नंबर|Plate or garage number
clear|Очистить поиск|Qidiruvni tozalash|Тоза кардани ҷустуҷӯ|Издөөнү тазалоо|Іздеуді тазалау|खोज मिटाएँ|Clear search
vehicleList|Машины|Mashinalar|Мошинҳо|Унаалар|Көліктер|गाड़ियाँ|Vehicles
count|Показано {found} из {total}|{total} tadan {found} tasi ko‘rsatilgan|Аз {total} мошин {found} нишон дода шуд|{total} унаанын {found}и көрсөтүлдү|{total} көліктің {found}-і көрсетілді|{total} में से {found} दिख रही हैं|Showing {found} of {total}
noResults|Машин с таким номером нет|Bunday raqamli mashina yo‘q|Бо ин рақам мошин ёфт нашуд|Мындай номерлүү унаа жок|Мұндай нөмірлі көлік жоқ|इस नंबर की गाड़ी नहीं मिली|No vehicles match this number
showAll|Показать еще {count}|Yana {count} tasini ko‘rsatish|Боз {count} мошинро нишон додан|Дагы {count} унааны көрсөтүү|Тағы {count} көлікті көрсету|{count} और दिखाएँ|Show {count} more
garage|Гаражный № {no}|Garaj raqami {no}|Рақами гаражӣ {no}|Гараж номери {no}|Гараж нөмірі {no}|गैराज नं. {no}|Garage no. {no}
normal|Норма|Me’yorda|Дар меъёр|Нормада|Қалыпты|सामान्य|Normal
anomaly|Требует внимания|Tekshirish kerak|Санҷидан лозим|Текшерүү керек|Тексеру керек|जाँच ज़रूरी है|Needs a check
failed|Перезаписать звук|Ovozni qayta yozing|Садоро аз нав сабт кунед|Үндү кайра жазыңыз|Дыбысты қайта жазыңыз|आवाज़ फिर से रिकॉर्ड करें|Record the sound again
noCheck|Нет проверки|Tekshiruv yo‘q|Санҷиш нашудааст|Текшерүү жок|Тексеру жоқ|जाँच नहीं हुई|No check
attention|Требует внимания|Tekshirish kerak|Санҷидан лозим|Текшерүү керек|Тексеру керек|जाँच ज़रूरी है|Needs attention
quarantine|Карантин|Yo‘lga chiqarmang|Ба роҳ набароред|Жолго чыгарбаңыз|Жолға шығармаңыз|ड्यूटी पर न भेजें|Keep off the road
fleetPriority|Машины, требующие внимания|Tekshirish kerak bo‘lgan mashinalar|Мошинҳое, ки бояд санҷид|Текшериле турган унаалар|Тексеру керек көліктер|जिन गाड़ियों की जाँच चाहिए|Vehicles needing attention
fleetEmpty|В этой группе нет машин|Bu guruhda mashina yo‘q|Дар ин гурӯҳ мошин нест|Бул топто унаа жок|Бұл топта көлік жоқ|इस समूह में कोई गाड़ी नहीं है|No vehicles in this group
engine|Двигатель|Dvigatel|Муҳаррик|Кыймылдаткыч|Қозғалтқыш|इंजन|Engine
checks|Прошлые проверки|Avvalgi tekshiruvlar|Санҷишҳои гузашта|Мурунку текшерүүлөр|Бұрынғы тексерулер|पिछली जाँचें|Past checks
lastCheck|Последняя проверка|Oxirgi tekshiruv|Санҷиши охирин|Акыркы текшерүү|Соңғы тексеру|आखिरी जाँच|Latest check
chooseCheck|Выберите проверку|Tekshiruvni tanlang|Санҷишро интихоб кунед|Текшерүүнү тандаңыз|Тексеруді таңдаңыз|जाँच चुनें|Choose a check
noChecks|Проверок пока нет|Hozircha tekshiruv yo‘q|Ҳоло санҷиш нест|Азырынча текшерүү жок|Әзірге тексеру жоқ|अभी कोई जाँच नहीं है|No checks yet
score|Оценка отклонения|Og‘ish balli|Баҳои инҳироф|Четтөө баасы|Ауытқу бағасы|गड़बड़ी का स्कोर|Anomaly score
noScore|Нет оценки|Ball yo‘q|Баҳо нест|Баа жок|Баға жоқ|कोई स्कोर नहीं|No score
trendNote|Шкала от 0 до 1. × – запись не подошла. Сравнивайте только записи, сделанные в одинаковых условиях.|Shkala 0 dan 1 gacha. × – yozuv yaroqsiz. Faqat bir xil sharoitda olingan yozuvlarni solishtiring.|Миқёс аз 0 то 1. × – сабт корношоям аст. Танҳо сабтҳои дар шароити яксон гирифташударо муқоиса кунед.|Шкала 0дөн 1ге чейин. × – жазуу жараксыз. Бирдей шартта жасалган жазууларды гана салыштырыңыз.|Шкала 0-ден 1-ге дейін. × – жазба жарамсыз. Тек бірдей жағдайда жазылған дыбыстарды салыстырыңыз.|स्कोर 0 से 1 तक है। × – रिकॉर्डिंग काम की नहीं है। एक जैसे हालात में की गई रिकॉर्डिंग ही मिलाएँ।|Scale: 0 to 1. × means the recording was unusable. Only compare recordings made under the same conditions.
pastTickets|Заявки по машине|Mashina bo‘yicha buyurtmalar|Дархостҳои ин мошин|Бул унаа боюнча өтүнмөлөр|Осы көлік бойынша өтінімдер|इस गाड़ी के वर्क ऑर्डर|Vehicle work orders
noTickets|Заявок пока нет|Hozircha buyurtma yo‘q|Ҳоло дархост нест|Азырынча өтүнмө жок|Әзірге өтінім жоқ|अभी कोई वर्क ऑर्डर नहीं है|No work orders yet
diagnose|Получить результат диагностики|Tekshiruv natijasini ochish|Натиҷаи санҷишро кушодан|Текшерүүнүн жыйынтыгын ачуу|Тексеру нәтижесін ашу|जाँच का नतीजा खोलें|Open check result
loading|Загружаем данные…|Ma’lumot yuklanmoqda…|Маълумот бор мешавад…|Маалымат жүктөлүүдө…|Дерек жүктелуде…|जानकारी आ रही है…|Loading…
loadFailed|Не удалось загрузить данные|Ma’lumot yuklanmadi|Маълумот бор нашуд|Маалымат жүктөлгөн жок|Дерек жүктелмеді|जानकारी नहीं आ सकी|Could not load data
retry|Повторить|Qayta urinish|Аз нав кӯшиш кунед|Кайра аракет кылуу|Қайталау|फिर कोशिश करें|Try again
serviceError|Ошибка сервиса ({code})|Xizmat xatosi ({code})|Хатои хидмат ({code})|Кызмат катасы ({code})|Қызмет қатесі ({code})|सेवा में गड़बड़ी ({code})|Service error ({code})
network|Нет связи. Проверьте интернет и попробуйте снова.|Aloqa yo‘q. Internetni tekshirib, qayta urinib ko‘ring.|Пайваст нест. Интернетро санҷеду аз нав кӯшиш кунед.|Байланыш жок. Интернетти текшерип, кайра аракет кылыңыз.|Байланыс жоқ. Интернетті тексеріп, қайта көріңіз.|कनेक्शन नहीं है। इंटरनेट जाँचकर फिर कोशिश करें।|No connection. Check your internet and try again.
normalTitle|Отклонений не выявлено|Og‘ish topilmadi|Инҳироф ёфт нашуд|Четтөө табылган жок|Ауытқу табылмады|कोई गड़बड़ी नहीं मिली|No anomaly found
anomalyTitle|Есть признаки отклонения|Og‘ish belgilari bor|Нишонаҳои инҳироф ҳастанд|Четтөөнүн белгилери бар|Ауытқу белгілері бар|गड़बड़ी के संकेत मिले|Signs of an anomaly
notApplicable|Тип отклонения не подтвержден|Og‘ish turi tasdiqlanmadi|Навъи инҳироф тасдиқ нашуд|Четтөөнүн түрү ырасталган жок|Ауытқу түрі расталмады|गड़बड़ी की वजह पक्की नहीं है|Anomaly type not confirmed
hypothesis|Возможная причина: {name}|Ehtimoliy sabab: {name}|Сабаби эҳтимолӣ: {name}|Мүмкүн болгон себеп: {name}|Ықтимал себеп: {name}|संभावित कारण: {name}|Possible cause: {name}
failedTitle|Запись не подошла|Yozuv yaroqsiz|Сабт корношоям аст|Жазуу жараган жок|Жазба жарамсыз|रिकॉर्डिंग जाँच के लायक नहीं है|Recording unusable
next|Что делать|Nima qilish kerak|Чӣ бояд кард|Эмне кылуу керек|Не істеу керек|क्या करें|What to do
nextFail|Запишите звук заново.|Ovozni qayta yozing.|Овозро аз нав сабт кунед.|Үндү кайра жазыңыз.|Дыбысты қайта жазыңыз.|आवाज़ फिर रिकॉर्ड करें।|Record the sound again.
nextNormal|Следуйте правилам вашего парка.|Avtopark qoidalariga rioya qiling.|Қоидаҳои автопаркро риоя кунед.|Автопарктын эрежелерин сактаңыз.|Автопарк ережесін сақтаңыз.|अपने बेड़े के नियम मानें।|Follow your fleet’s procedures.
nextAnomaly|Осмотрите машину на месте.|Mashinani joyida ko‘rikdan o‘tkazing.|Мошинро дар ҷояш аз назар гузаронед.|Унааны жеринде карап чыгыңыз.|Көлікті орнында қарап шығыңыз.|गाड़ी को मौके पर जाँचें।|Inspect the vehicle in person.
low|Низкий|Past|Паст|Төмөн|Төмен|कम|Low
medium|Средний|O‘rta|Миёна|Орточо|Орташа|मध्यम|Medium
high|Высокий|Yuqori|Баланд|Жогору|Жоғары|ज़्यादा|High
priority|Приоритет|Ustuvorlik|Афзалият|Артыкчылык|Басымдық|प्राथमिकता|Priority
whyPriority|Почему такой приоритет|Nega bunday ustuvorlik|Чаро ин афзалият|Эмне үчүн мындай артыкчылык|Неге осындай басымдық|यह प्राथमिकता क्यों|Why this priority
whyResult|Почему такой результат|Nega bunday natija|Чаро чунин натиҷа|Эмне үчүн мындай жыйынтык|Неге осындай нәтиже|यह नतीजा क्यों|Why this result
noReasons|Причины не указаны|Sabablar ko‘rsatilmagan|Сабабҳо нишон дода нашудаанд|Себептери көрсөтүлгөн эмес|Себептері көрсетілмеген|वजह नहीं बताई गई|No reasons given
important|Важно|Muhim|Муҳим|Маанилүү|Маңызды|ज़रूरी|Important
metrics|Цифры проверки|Tekshiruv tafsilotlari|Ҷузъиёти санҷиш|Текшерүүнүн чоо-жайы|Тексеру мәліметтері|जाँच का विवरण|Check details
confidence|Уверенность модели|Model ishonchi|Эътимоди модел|Моделдин ишеними|Модель сенімділігі|मॉडल का भरोसा|Model confidence
quality|Качество записи|Yozuv sifati|Сифати сабт|Жазуунун сапаты|Жазба сапасы|रिकॉर्डिंग की गुणवत्ता|Recording quality
good|Хорошее|Yaxshi|Хуб|Жакшы|Жақсы|अच्छी|Good
noisy|С помехами|Shovqinli|Бо халал|Ызы-чуу бар|Шулы|शोर है|Noisy
poor|Плохое|Yomon|Паст|Начар|Нашар|खराब|Poor
noData|Нет данных|Ma’lumot yo‘q|Маълумот нест|Маалымат жок|Дерек жоқ|जानकारी नहीं|No data
sources|Источники|Manbalar|Манбаъҳо|Булактар|Дереккөздер|स्रोत|Sources
source|Источник {n}: {name}, страница {page}|Manba {n}: {name}, {page}-bet|Манбаи {n}: {name}, саҳифаи {page}|Булак {n}: {name}, {page}-бет|Дереккөз {n}: {name}, {page}-бет|स्रोत {n}: {name}, पन्ना {page}|Source {n}: {name}, page {page}
pageRef|{name}, стр. {page}|{name}, {page}-bet|{name}, саҳ. {page}|{name}, {page}-бет|{name}, {page}-бет|{name}, पन्ना {page}|{name}, p. {page}
steps|Как помощник искал ответ|Yordamchi nima qildi|Ёрдамчӣ чӣ кор кард|Жардамчы эмне кылды|Көмекші не істеді|सहायक ने क्या किया|What the assistant did
working|В работе|Bajarilmoqda|Дар кор|Аткарылууда|Орындалуда|काम जारी है|In progress
error|Ошибка|Xato|Хато|Ката|Қате|गड़बड़ी|Error
done|Готово|Tayyor|Тайёр|Даяр|Дайын|हो गया|Done
mechanic|Вы|Siz|Шумо|Сиз|Сіз|आप|You
answer|Объяснение помощника|Yordamchi izohi|Шарҳи ёрдамчӣ|Жардамчынын түшүндүрмөсү|Көмекшінің түсіндірмесі|सहायक की व्याख्या|Assistant’s explanation
result|Результат проверки|Tekshiruv natijasi|Натиҷаи санҷиш|Текшерүү жыйынтыгы|Тексеру нәтижесі|जाँच का नतीजा|Check result
pending|Готовлю ответ…|Javob tayyorlayapman…|Ҷавобро тайёр мекунам…|Жооп даярдап жатам…|Жауап дайындап жатырмын…|जवाब तैयार हो रहा है…|Preparing an answer…
stepDiagnose|Проверяю запись…|Yozuvni tekshiryapman…|Сабтро месанҷам…|Жазууну текшерип жатам…|Жазбаны тексеріп жатырмын…|रिकॉर्डिंग की जाँच हो रही है…|Checking the recording…
stepHistory|Смотрю историю машины…|Mashina tarixini ko‘ryapman…|Санҷишҳои гузаштаро мебинам…|Унаанын тарыхын карап жатам…|Көлік тарихын қарап жатырмын…|गाड़ी की पिछली जाँचें देख रहे हैं…|Checking vehicle history…
stepSearch|Ищу в руководстве…|Qo‘llanmadan izlayapman…|Дар дастур меҷӯям…|Колдонмодон издеп жатам…|Нұсқаулықтан іздеп жатырмын…|मैनुअल में ढूँढ रहे हैं…|Searching the manual…
stepRead|Читаю страницу руководства…|Qo‘llanma betini o‘qiyapman…|Саҳифаи дастурро мехонам…|Колдонмонун бетин окуп жатам…|Нұсқаулық бетін оқып жатырмын…|मैनुअल का पन्ना पढ़ रहे हैं…|Reading the manual…
stepFault|Уточняю тип отклонения…|Og‘ish turini aniqlayapman…|Навъи инҳирофро месанҷам…|Четтөөнүн түрүн тактап жатам…|Ауытқу түрін анықтап жатырмын…|गड़बड़ी की वजह देख रहे हैं…|Checking the possible fault…
stepDraft|Готовлю черновик…|Qoralama tayyorlayapman…|Пешнавис месозам…|Өтүнмөнүн долбоорун даярдап жатам…|Өтінім жобасын дайындап жатырмын…|मसौदा तैयार हो रहा है…|Preparing a draft…
openReceipt|Открыть квитанцию|Kvitansiyani ochish|Кушодани расид|Дүмүрчөктү ачуу|Түбіртекті ашу|रसीद खोलें|Open receipt
createDraft|Создать заявку|Ta’mirlash buyurtmasini tayyorlash|Дархости таъмирро омода кардан|Оңдоо өтүнмөсүн даярдоо|Жөндеуге өтінім дайындау|मरम्मत का वर्क ऑर्डर तैयार करें|Prepare a repair work order
openDraft|Открыть черновик|Qoralamani ochish|Кушодани пешнавис|Долбоорду ачуу|Жобаны ашу|मसौदा खोलें|Open draft
question|Вопрос о машине|Mashina haqida savol|Савол дар бораи мошин|Унаа боюнча суроо|Көлік туралы сұрақ|गाड़ी पर सवाल|Question about the vehicle
send|Отправить|Yuborish|Фиристодан|Жөнөтүү|Жіберу|भेजें|Send
sendQuestion|Отправить вопрос|Savolni yuborish|Фиристодани савол|Суроону жөнөтүү|Сұрақты жіберу|सवाल भेजें|Send question
mic|Вопрос голосом|Ovozli savol|Саволи овозӣ|Үн менен суроо|Дауыспен сұрау|आवाज़ से सवाल पूछें|Ask by voice
micShort|Голосом|Ovoz|Бо овоз|Үн менен|Дауыспен|बोलें|Speak
micStop|Стоп|To‘xtatish|Қатъ кардан|Токтотуу|Тоқтату|रोकें|Stop
micAsk|Запрашиваем доступ к микрофону…|Mikrofonga ruxsat so‘ralmoqda…|Дастрасӣ ба микрофонро мепурсем…|Микрофонго уруксат суралууда…|Микрофонға рұқсат сұралуда…|माइक की अनुमति माँग रहे हैं…|Requesting microphone access…
micRecording|Слушаю…|Tinglayapman…|Гӯш мекунам…|Угуп жатам…|Тыңдап тұрмын…|सुन रहा हूँ…|Listening…
micTranscribe|Распознаем речь…|Nutq matnga o‘girilmoqda…|Овоз ба матн табдил меёбад…|Үн текстке айланууда…|Сөз мәтінге айналуда…|बोली को लिख रहे हैं…|Transcribing…
micReady|Проверьте текст и нажмите «Отправить».|Matnni tekshirib, «Yuborish»ni bosing.|Матнро санҷед ва «Фиристодан»-ро пахш кунед.|Текстти текшерип, «Жөнөтүү» баскычын басыңыз.|Мәтінді тексеріп, «Жіберу» түймесін басыңыз.|लिखा हुआ देखकर «भेजें» दबाएँ।|Check the text, then press Send.
micDenied|Доступ к микрофону закрыт. Разрешите его в браузере или напишите вопрос.|Mikrofonga ruxsat yo‘q. Brauzerda ruxsat bering yoki savol yozing.|Дастрасӣ ба микрофон баста аст. Дар браузер иҷозат диҳед ё савол нависед.|Микрофонго уруксат жок. Браузерден уруксат бериңиз же суроону жазыңыз.|Микрофонға рұқсат жоқ. Браузерден рұқсат беріңіз немесе сұрақты жазыңыз.|माइक की अनुमति नहीं है। ब्राउज़र में अनुमति दें या सवाल लिखें।|Microphone access is blocked. Allow it in your browser or type your question.
micUnsupported|Этот браузер не умеет записывать звук. Напишите вопрос.|Bu brauzer ovoz yoza olmaydi. Savol yozing.|Ин браузер овоз сабт карда наметавонад. Савол нависед.|Бул браузер үн жаза албайт. Суроону жазыңыз.|Бұл браузер дыбыс жаза алмайды. Сұрақты жазыңыз.|यह ब्राउज़र आवाज़ रिकॉर्ड नहीं कर सकता। सवाल लिखें।|This browser cannot record audio. Type your question instead.
micSecure|Для записи откройте сайт по HTTPS или напишите вопрос.|Yozish uchun saytni HTTPS orqali oching yoki savol yozing.|Барои сабт сомонаро бо HTTPS кушоед ё савол нависед.|Үн жазуу үчүн сайтты HTTPS менен ачыңыз же суроону жазыңыз.|Дыбыс жазу үшін сайтты HTTPS арқылы ашыңыз немесе сұрақты жазыңыз.|रिकॉर्डिंग के लिए साइट HTTPS पर खोलें या सवाल लिखें।|Open the site over HTTPS to record, or type your question.
micMissing|Микрофон не найден. Подключите его или напишите вопрос.|Mikrofon topilmadi. Uni ulang yoki savol yozing.|Микрофон ёфт нашуд. Онро пайваст кунед ё савол нависед.|Микрофон табылган жок. Туташтырыңыз же суроону жазыңыз.|Микрофон табылмады. Оны қосыңыз немесе сұрақты жазыңыз.|माइक नहीं मिला। उसे जोड़ें या सवाल लिखें।|No microphone found. Connect one or type your question.
micFailed|Не удалось записать звук. Попробуйте еще раз или напишите вопрос.|Ovoz yozilmadi. Qayta urinib ko‘ring yoki savol yozing.|Овоз сабт нашуд. Аз нав кӯшиш кунед ё савол нависед.|Үн жазылган жок. Кайра аракет кылыңыз же суроону жазыңыз.|Дыбыс жазылмады. Қайта көріңіз немесе сұрақты жазыңыз.|आवाज़ रिकॉर्ड नहीं हुई। फिर कोशिश करें या सवाल लिखें।|Could not record audio. Try again or type your question.
micEmpty|Речь не слышно. Запишите еще раз или напишите вопрос.|Gap eshitilmadi. Qayta yozing yoki savol yozing.|Сухан шунида нашуд. Аз нав сабт кунед ё савол нависед.|Сөз угулган жок. Кайра жазыңыз же суроону териңиз.|Сөз естілмеді. Қайта жазыңыз немесе сұрақты теріңіз.|बोली सुनाई नहीं दी। फिर रिकॉर्ड करें या सवाल लिखें।|No speech detected. Record again or type your question.
micService|Не удалось распознать речь. Попробуйте еще раз или напишите вопрос.|Nutq matnga o‘girilmadi. Qayta urinib ko‘ring yoki savol yozing.|Овоз ба матн табдил наёфт. Аз нав кӯшиш кунед ё савол нависед.|Үн текстке айланган жок. Кайра аракет кылыңыз же суроону жазыңыз.|Сөз мәтінге айналмады. Қайта көріңіз немесе сұрақты жазыңыз.|बोली लिखी नहीं जा सकी। फिर कोशिश करें या सवाल लिखें।|Could not transcribe the audio. Try again or type your question.
streamMissing|Не удалось начать получать ответ.|Javob kelmadi.|Ҷавоб наомад.|Жооп келген жок.|Жауап келмеді.|जवाब नहीं आया।|Could not start receiving the reply.
streamCut|Связь прервалась. Ответ может быть неполным.|Aloqa uzildi. Javob to‘liq bo‘lmasligi mumkin.|Пайваст қатъ шуд. Ҷавоб шояд нопурра бошад.|Байланыш үзүлдү. Жооп толук болбошу мүмкүн.|Байланыс үзілді. Жауап толық болмауы мүмкін.|कनेक्शन टूट गया। जवाब अधूरा हो सकता है।|The connection dropped. The reply may be incomplete.
chatError|Не удалось получить ответ.|Javob olinmadi.|Ҷавоб гирифта нашуд.|Жооп алынган жок.|Жауап алынбады.|जवाब नहीं मिल सका।|Could not get a reply.
noDiagnosis|Результат проверки не пришел.|Tekshiruv natijasi kelmadi.|Натиҷаи санҷиш наомад.|Текшерүү жыйынтыгы келген жок.|Тексеру нәтижесі келмеді.|जाँच का नतीजा नहीं आया।|No check result received.
noDraft|Черновик не найден|Qoralama topilmadi|Пешнавис ёфт нашуд|Долбоор табылган жок|Жоба табылмады|मसौदा नहीं मिला|Draft not found
priorityReason|Почему меняете приоритет?|Nega ustuvorlikni o‘zgartiryapsiz?|Чаро афзалиятро иваз мекунед?|Артыкчылыкты эмне үчүн өзгөртүп жатасыз?|Басымдықты неге өзгертесіз?|प्राथमिकता क्यों बदल रहे हैं?|Why change the priority?
choosePriority|Выберите приоритет|Ustuvorlikni tanlang|Афзалиятро интихоб кунед|Артыкчылыкты тандаңыз|Басымдықты таңдаңыз|प्राथमिकता चुनें|Select priority
faultType|Тип отклонения|Og‘ish turi|Навъи инҳироф|Четтөөнүн түрү|Ауытқу түрі|गड़बड़ी का प्रकार|Anomaly type
conclusion|Заключение|Xulosa|Хулоса|Корутунду|Қорытынды|निष्कर्ष|Conclusion
work|Работы|Ishlar|Корҳо|Жумуштар|Жұмыстар|करने के काम|Jobs
parts|Запчасти|Ehtiyot qismlar|Қисмҳои эҳтиётӣ|Тетиктер|Қосалқы бөлшектер|स्पेयर पार्ट्स|Spare parts
newLine|Каждый пункт с новой строки|Har bir band yangi satrda|Ҳар банд дар сатри нав|Ар бир пункт жаңы сапта|Әр тармақ жаңа жолда|हर चीज़ नई लाइन में लिखें|One item per line
unsent|Не отправлена|Yuborilmagan|Фиристода нашудааст|Жөнөтүлө элек|Жіберілмеген|अभी नहीं भेजा गया|Not sent
sending|Отправляем…|Yuborilmoqda…|Фиристода мешавад…|Жөнөтүлүүдө…|Жіберілуде…|भेज रहे हैं…|Sending…
confirm|Отправить заявку|Buyurtmani yuborish|Дархостро фиристодан|Өтүнмөнү жөнөтүү|Өтінімді жіберу|वर्क ऑर्डर भेजें|Send work order
confirmNote|Заявка появится в системе ремонта.|Buyurtma ta’mirlash tizimida ko‘rinadi.|Дархост дар низоми таъмир пайдо мешавад.|Өтүнмө оңдоо системасында көрүнөт.|Өтінім жөндеу жүйесінде пайда болады.|वर्क ऑर्डर मरम्मत सिस्टम में दिखेगा।|The work order will appear in the repair system.
reasonLine|Причина изменения приоритета: {reason}|Ustuvorlikni o‘zgartirish sababi: {reason}|Сабаби ивази афзалият: {reason}|Артыкчылыкты өзгөртүү себеби: {reason}|Басымдықты өзгерту себебі: {reason}|प्राथमिकता बदलने की वजह: {reason}|Reason for changing priority: {reason}
needConclusion|Введите заключение.|Xulosani yozing.|Хулосаро нависед.|Корутундуну жазыңыз.|Қорытындыны жазыңыз.|निष्कर्ष लिखें।|Enter a conclusion.
needReason|Укажите причину изменения приоритета.|Ustuvorlikni nega o‘zgartirganingizni yozing.|Сабаби ивази афзалиятро нависед.|Артыкчылыкты эмне үчүн өзгөрткөнүңүздү жазыңыз.|Басымдықты неге өзгерткеніңізді жазыңыз.|प्राथमिकता बदलने की वजह लिखें।|Enter a reason for changing priority.
noTicketId|Номер заявки не пришел.|Buyurtma raqami kelmadi.|Рақами дархост наомад.|Өтүнмө номери келген жок.|Өтінім нөмірі келмеді.|वर्क ऑर्डर नंबर नहीं मिला।|No work order number received.
confirmUncertain|Нет подтверждения. Проверьте, появилась ли заявка в ТОиР, прежде чем отправлять ее снова.|Tasdiq kelmadi. Qayta yuborishdan oldin buyurtma texnik xizmat tizimida bor-yo‘qligini tekshiring.|Тасдиқ наомад. Пеш аз фиристодани дубора санҷед, ки дархост дар низоми таъмир ҳаст ё не.|Ырастоо келген жок. Кайра жөнөтөрдөн мурун өтүнмө тейлөө тутумунда бар-жогун текшериңиз.|Растау келмеді. Қайта жібермес бұрын өтінімнің жөндеу жүйесінде барын тексеріңіз.|पुष्टि नहीं मिली। दोबारा भेजने से पहले देखें कि वर्क ऑर्डर रखरखाव सिस्टम में है या नहीं।|No confirmation received. Check the maintenance system before sending again.
noReceipt|Квитанция недоступна|Kvitansiya ochilmadi|Расид дастрас нест|Дүмүрчөк жеткиликсиз|Түбіртек қолжетімсіз|रसीद नहीं मिली|Receipt unavailable
machine|Машина|Mashina|Мошин|Унаа|Көлік|गाड़ी|Vehicle
check|Проверка|Tekshiruv|Санҷиш|Текшерүү|Тексеру|जाँच|Check
accepted|Принята в ТОиР|Texnik xizmat tizimi qabul qildi|Низоми таъмир қабул кард|Тейлөө тутуму кабыл алды|Жөндеу жүйесі қабылдады|रखरखाव सिस्टम ने स्वीकार किया|Accepted by maintenance
sentDetails|Что отправили|Nima yuborildi|Чӣ фиристода шуд|Эмне жөнөтүлдү|Не жіберілді|क्या भेजा गया|What was sent
backPark|К списку машин|Mashinalar ro‘yxatiga|Ба рӯйхати мошинҳо|Унаалар тизмесине|Көлік тізіміне|गाड़ियों की सूची पर जाएँ|Back to vehicles
closeManual|Закрыть руководство|Qo‘llanmani yopish|Пӯшидани дастур|Колдонмону жабуу|Нұсқаулықты жабу|मैनुअल बंद करें|Close manual
manual|Руководство|Qo‘llanma|Дастур|Колдонмо|Нұсқаулық|मैनुअल|Manual
openPage|Открываем страницу {page}…|{page}-bet ochilmoqda…|Саҳифаи {page} кушода мешавад…|{page}-бет ачылууда…|{page}-бет ашылуда…|पन्ना {page} खुल रहा है…|Opening page {page}…
imageLoading|Загружаем изображение…|Rasm yuklanmoqda…|Тасвир бор мешавад…|Сүрөт жүктөлүүдө…|Сурет жүктелуде…|तस्वीर लोड हो रही है…|Loading image…
imageFailed|Изображение не загрузилось.|Rasm yuklanmadi.|Тасвир бор нашуд.|Сүрөт жүктөлгөн жок.|Сурет жүктелмеді.|तस्वीर लोड नहीं हुई।|Image did not load.
zoomOut|Уменьшить|Kichraytirish|Хурд кардан|Кичирейтүү|Кішірейту|छोटा करें|Zoom out
zoomIn|Увеличить|Kattalashtirish|Калон кардан|Чоңойтуу|Үлкейту|बड़ा करें|Zoom in
prevPage|Предыдущая страница|Oldingi bet|Саҳифаи пешина|Мурунку бет|Алдыңғы бет|पिछला पन्ना|Previous page
nextPage|Следующая страница|Keyingi bet|Саҳифаи баъдӣ|Кийинки бет|Келесі бет|अगला पन्ना|Next page
pageNumber|{page} из {total}|{page} / {total}|{page} аз {total}|{page} / {total}|{page} / {total}|{total} में से {page}|{page} of {total}
pageText|Текст страницы|Bet matni|Матни саҳифа|Беттин тексти|Бет мәтіні|पन्ने का पाठ|Page text
quote|Цитата из ответа|Javobdagi iqtibos|Иқтибос аз ҷавоб|Жооптон үзүндү|Жауаптан дәйексөз|जवाब में दिया अंश|Quote from answer
pageUnavailable|Страница недоступна|Bet ochilmadi|Саҳифа дастрас нест|Бет жеткиликсиз|Бет қолжетімсіз|पन्ना नहीं खुला|Page unavailable
close|Закрыть|Yopish|Пӯшидан|Жабуу|Жабу|बंद करें|Close
stopRelease|Дефектовка до выпуска в рейс|Reysdan oldin nosozlikni tekshirish|Ташхиси носозӣ пеш аз рейс|Рейске чейин дефектовка|Рейске дейін ақауды тексеру|लाइन पर भेजने से पहले जाँच|Fault inspection before release
noPastChecks|Прошлых проверок нет|Avvalgi tekshiruvlar yo‘q|Санҷиши пешина нест|Мурунку текшерүү жок|Бұрынғы тексерулер жоқ|कोई पिछली जाँच नहीं है|No past checks
recordTipLoud|Звук был слишком громким для микрофона: поставьте прибор дальше от выпускной трубы и вентилятора.|Ovoz mikrofon uchun juda baland edi: qurilmani chiqarish trubasi va ventilyatordan uzoqroq qo‘ying.|Садо барои микрофон хеле баланд буд: дастгоҳро аз қубури газбарор ва вентилятор дуртар гузоред.|Үн микрофон үчүн өтө катуу болду: аспапты чыгаруучу түтүктөн жана желдеткичтен алысыраак коюңуз.|Дыбыс микрофон үшін тым қатты болды: құрылғыны шығару құбыры мен желдеткіштен алысырақ қойыңыз.|आवाज़ माइक्रोफ़ोन के लिए बहुत तेज़ थी: डिवाइस को एग्ज़ॉस्ट पाइप और पंखे से दूर रखें।|The sound was too loud for the microphone: place the recorder further from the exhaust pipe and fan.
recordTipIdle|Обороты не успели установиться: прогрейте двигатель и начинайте запись, когда холостой ход станет ровным.|Aylanishlar barqarorlashmadi: dvigatelni qizdiring va salt yurish tekis bo‘lganda yozishni boshlang.|Гардишҳо устувор нашуданд: муҳаррикро гарм кунед ва вақте ки гардиши холӣ ҳамвор шуд, сабтро оғоз кунед.|Айлануулар турукташа элек: кыймылдаткычты жылытып, бош жүрүш бир калыпка келгенде жаза баштаңыз.|Айналым тұрақталмады: қозғалтқышты қыздырып, бос жүріс біркелкі болғанда жазуды бастаңыз.|आरपीएम स्थिर नहीं हुए: इंजन गर्म करें और आइडलिंग स्थिर होने पर रिकॉर्डिंग शुरू करें।|Engine speed had not settled: warm the engine up and start recording once idle is steady.
recordTipNoise|Двигатель заглушил шум поста: на время записи выключите компрессор и соседние машины.|Dvigatel ovozini post shovqini bosib ketdi: yozuv vaqtida kompressor va yonidagi mashinalarni o‘chiring.|Садои муҳаррикро садои пост пахш кард: ҳангоми сабт компрессор ва мошинҳои наздикро хомӯш кунед.|Кыймылдаткычтын үнүн посттун ызы-чуусу басып кетти: жазуу учурунда компрессорду жана жанындагы машиналарды өчүрүңүз.|Қозғалтқыш дыбысын пост шуы басып кетті: жазу кезінде компрессор мен жанындағы көліктерді өшіріңіз.|पोस्ट के शोर में इंजन की आवाज़ दब गई: रिकॉर्डिंग के दौरान कंप्रेसर और पास की गाड़ियाँ बंद करें।|Workshop noise drowned out the engine: switch off the compressor and nearby vehicles while recording.
rejectReason|Причина: {reason}.|Sabab: {reason}.|Сабаб: {reason}.|Себеп: {reason}.|Себеп: {reason}.|कारण: {reason}.|Reason: {reason}.
rerecordWhere|Перезапись делается на микрофонном посту в смотровой яме. Новая проверка появится в этой карточке сама.|Qayta yozuv ko‘rik chuquridagi mikrofon postida qilinadi. Yangi tekshiruv shu kartochkada o‘zi paydo bo‘ladi.|Сабти нав дар пости микрофонӣ дар чоҳи муоина анҷом дода мешавад. Санҷиши нав дар ҳамин корт худ пайдо мешавад.|Кайра жазуу текшерүү чуңкурундагы микрофон постунда жасалат. Жаңы текшерүү ушул карточкада өзү пайда болот.|Қайта жазу қарау шұңқырындағы микрофон постында жасалады. Жаңа тексеру осы карточкада өзі пайда болады.|दोबारा रिकॉर्डिंग निरीक्षण गड्ढे के माइक्रोफ़ोन पोस्ट पर होती है। नई जाँच इसी कार्ड में अपने आप दिखेगी।|Re-recording is done at the microphone post in the inspection pit. The new check will appear in this card automatically.
recordTip1|Записывайте там, где тихо.|Tinch joyda yozing.|Дар ҷои ором сабт кунед.|Тынч жерде жазыңыз.|Тыныш жерде жазыңыз.|शांत जगह पर रिकॉर्ड करें।|Record somewhere quiet.
recordTip2|Держите прибор неподвижно.|Qurilmani qimirlatmay ushlang.|Дастгоҳро беҳаракат нигоҳ доред.|Аспапты кыймылдатпай кармаңыз.|Құрылғыны қозғалтпай ұстаңыз.|डिवाइस को स्थिर रखें।|Keep the recorder still.
recordTip3|Не разговаривайте во время записи.|Yozuv paytida gaplashmang.|Ҳангоми сабт суҳбат накунед.|Жазып жатканда сүйлөбөңүз.|Жазу кезінде сөйлемеңіз.|रिकॉर्डिंग के दौरान बात न करें।|Do not talk while recording.
why|Почему|Sababi|Чаро|Эмне үчүн|Неге|क्यों|Why
priorityLine|Приоритет: {level}|Ustuvorlik: {level}|Афзалият: {level}|Артыкчылык: {level}|Басымдық: {level}|प्राथमिकता: {level}|Priority: {level}
more|Показать выдержку полностью|Ko‘proq|Бештар|Дагы|Толығырақ|और पढ़ें|More
less|Свернуть|Yig‘ish|Пинҳон кардан|Жыйноо|Жию|कम दिखाएँ|Show less
zoom|Масштаб|Masshtab|Миқёс|Масштаб|Масштаб|ज़ूम|Zoom
note|Учтите|E’tibor bering|Диққат кунед|Эске алыңыз|Ескеріңіз|ध्यान दें|Keep in mind
scoreChart|Оценка отклонения по проверкам|Tekshiruvlar bo‘yicha og‘ish bahosi|Баҳои инҳироф аз рӯи санҷишҳо|Текшерүүлөр боюнча четтөө баасы|Тексерулер бойынша ауытқу бағасы|जाँचों के अनुसार विचलन स्कोर|Deviation score by check
scoreScale|0 – норма, 1 – сильное отклонение|0 – me’yor, 1 – kuchli og‘ish|0 – меъёр, 1 – инҳирофи сахт|0 – норма, 1 – катуу четтөө|0 – қалыпты, 1 – күшті ауытқу|0 – सामान्य, 1 – गंभीर विचलन|0 – normal, 1 – strong deviation
noScore|нет оценки|baho yo‘q|баҳо нест|баа жок|баға жоқ|स्कोर नहीं|no score
pageShort|стр. {page}|{page}-bet|саҳ. {page}|{page}-бет|{page}-бет|पृष्ठ {page}|p. {page}
logout|Выйти|Chiqish|Баромадан|Чыгуу|Шығу|लॉग आउट|Log out
fleetTitle|Главный механик|Bosh mexanik|Механики калон|Башкы механик|Бас механик|मुख्य मैकेनिक|Chief mechanic
fleetTotal|Машин в парке: {n}|Parkdagi mashinalar: {n}|Мошинҳо дар парк: {n}|Парктагы машиналар: {n}|Парктегі көліктер: {n}|पार्क में वाहन: {n}|Vehicles in the fleet: {n}
fleetQueue|Очередь на дефектовку|Nosozlikni aniqlash navbati|Навбат ба ташхиси нуқсон|Дефектовка кезеги|Ақау анықтау кезегі|जाँच की कतार|Inspection queue
fleetFirst|Кого ставить на дефектовку первым|Birinchi navbatda nosozlikni aniqlashga|Аввал ба ташхиси нуқсон кадом мошин|Биринчи кезекте дефектовкага|Бірінші кезекте ақау анықтауға|सबसे पहले जाँच के लिए|Send for inspection first
fleetGroup|Группа: {name}|Guruh: {name}|Гурӯҳ: {name}|Топ: {name}|Топ: {name}|समूह: {name}|Group: {name}
showNormal|Показать машины в норме ({count})|Me’yordagi mashinalarni ko‘rsatish ({count})|Мошинҳои дар меъёрро нишон додан ({count})|Нормадагы машиналарды көрсөтүү ({count})|Қалыпты көліктерді көрсету ({count})|सामान्य वाहन दिखाएँ ({count})|Show vehicles in normal state ({count})
fleetBriefStop|Дефектовка до выпуска: {n}|Reysdan oldin tekshiruv: {n}|Ташхис пеш аз рейс: {n}|Рейске чейин дефектовка: {n}|Рейске дейін тексеру: {n}|भेजने से पहले जाँच: {n}|Inspect before release: {n}
fleetBriefAttention|Требуют внимания: {n}.|E’tibor talab qiladi: {n}.|Диққатро талаб мекунанд: {n}.|Көңүл бурууну талап кылат: {n}.|Назар аударуды қажет етеді: {n}.|ध्यान चाहिए: {n}.|Need attention: {n}.
fleetBriefFailed|Нужна перезапись звука: {n}|Ovozni qayta yozish kerak: {n}|Садо бояд аз нав сабт шавад: {n}|Үндү кайра жазуу керек: {n}|Дыбысты қайта жазу керек: {n}|आवाज़ फिर से रिकॉर्ड करनी है: {n}|Sound must be recorded again: {n}
fleetBriefTickets|Заявок в работе: {n}.|Ishdagi buyurtmalar: {n}.|Дархостҳои дар иҷро: {n}.|Аткарылып жаткан өтүнмөлөр: {n}.|Жұмыстағы өтінімдер: {n}.|प्रगति में अनुरोध: {n}.|Requests in progress: {n}.
checkedLabel|Проверка|Tekshiruv|Санҷиш|Текшерүү|Тексеру|जाँच|Check
checkedAt|Дата и время проверки|Tekshiruv sanasi va vaqti|Сана ва вақти санҷиш|Текшерүүнүн күнү жана убактысы|Тексерілген күн мен уақыт|जाँच की तारीख और समय|Check date and time
overrideLabel|Причина изменения приоритета|Ustuvorlikni o‘zgartirish sababi|Сабаби иваз кардани афзалият|Артыкчылыкты өзгөртүүнүн себеби|Басымдықты өзгерту себебі|प्राथमिकता बदलने की वजह|Reason for changing priority
unresolved|Прошлое отклонение еще не закрыто|Oldingi og‘ish hali yopilmagan|Норасоии қаблӣ ҳанӯз бартараф нашудааст|Мурунку четтөө али жабыла элек|Бұрынғы ауытқу әлі жабылған жоқ|पिछली गड़बड़ी अभी दूर नहीं हुई है|A previous fault is still unresolved
answerDetail|Режим ответа|Javob rejimi|Шеваи ҷавоб|Жооп режими|Жауап режимі|जवाब का तरीका|Answer mode
brief|Коротко|Qisqa|Кӯтоҳ|Кыскача|Қысқаша|संक्षेप में|Brief
detailed|Подробно|Batafsil|Муфассал|Кеңири|Толық|विस्तार से|Detailed
detailHint|Подробно – каждый шаг объясняется простыми словами|Batafsil – har bir qadam oddiy tilda tushuntiriladi|Муфассал – ҳар қадам бо суханони сода шарҳ дода мешавад|Кеңири – ар бир кадам жөнөкөй сөздөр менен түшүндүрүлөт|Толық – әр қадам қарапайым тілмен түсіндіріледі|विस्तार से – हर कदम आसान शब्दों में समझाया जाता है|Detailed – each step explained in plain language
inspectFirst|Сначала осмотрите узел на машине|Avval mashinadagi uzelni ko‘zdan kechiring|Аввал ҷузъро дар мошин аз назар гузаронед|Адегенде унаадагы түйүндү карап чыгыңыз|Алдымен көліктегі торапты қарап шығыңыз|पहले गाड़ी में उस हिस्से की जाँच करें|Inspect the affected part on the vehicle first
noTicketTitle|Заявку продукт не отправляет|Ariza yuborilmaydi|Дархост фиристода намешавад|Арыз жөнөтүлбөйт|Өтінім жіберілмейді|आवेदन नहीं भेजा जाएगा|No repair request will be sent
noTicketWhy|В руководстве на этот двигатель нет инструкции по найденному узлу. Повторите проверку или оформите дефектовку по порядку парка – текст рекомендации ниже.|Bu dvigatel qo‘llanmasida topilgan uzel bo‘yicha ko‘rsatma yo‘q. Tekshiruvni takrorlang yoki defektovkani park tartibida rasmiylashtiring – tavsiya matni quyida.|Дар дастури ин муҳаррик барои ин ҷузъ дастур нест. Санҷишро такрор кунед ё ташхисро бо тартиби парк расмӣ кунед – матни тавсия дар поён.|Бул кыймылдаткычтын колдонмосунда табылган түйүн боюнча нускама жок. Текшерүүнү кайталаңыз же дефектовканы парктын тартиби менен тариздеңиз – сунуштун тексти төмөндө.|Бұл қозғалтқыш нұсқаулығында табылған түйін бойынша нұсқаулық жоқ. Тексеруді қайталаңыз немесе ақауды тексеруді парк тәртібімен рәсімдеңіз – ұсыныс мәтіні төменде.|इस इंजन की पुस्तिका में इस हिस्से के लिए कोई निर्देश नहीं है। जाँच दोबारा करें या बेड़े के नियम से जाँच दर्ज करें – सिफ़ारिश का पाठ नीचे है।|The manual for this engine has no instruction for this unit. Repeat the check or register the fault inspection under your fleet procedure – the recommendation text is below.
defectNote|Текст рекомендации на дефектовку|Defektovka bo‘yicha tavsiya matni|Матни тавсия барои ташхис|Дефектовка боюнча сунуштун тексти|Ақауды тексеру бойынша ұсыныс мәтіні|जाँच की सिफ़ारिश का पाठ|Recommendation text for fault inspection
copyText|Скопировать текст|Matnni nusxalash|Нусха бардоштан|Текстти көчүрүү|Мәтінді көшіру|पाठ कॉपी करें|Copy text
copiedText|Текст скопирован|Matn nusxalandi|Матн нусха шуд|Текст көчүрүлдү|Мәтін көшірілді|पाठ कॉपी हो गया|Text copied
confThreshold|порог заявки {v}|ariza chegarasi {v}|ҳадди дархост {v}|арыз чеги {v}|өтінім шегі {v}|आवेदन सीमा {v}|request threshold {v}
inspectionConfirmed|Признак подтвержден осмотром|Alomat ko‘rikda tasdiqlandi|Аломат ҳангоми муоина тасдиқ шуд|Белги кароодо тастыкталды|Белгі қарап тексеру кезінде расталды|जाँच में लक्षण की पुष्टि हुई|I inspected the part and confirmed the symptom
inspectBeforeSend|Отметьте выше, что осмотр подтвердил признак. После этого заявку можно отправить.|Buyurtmani yuborish uchun ko‘rikni tasdiqlang.|Барои фиристодани дархост муоинаро тасдиқ кунед.|Өтүнмөнү жөнөтүү үчүн кароону ырастаңыз.|Өтінімді жіберу үшін қарап тексергеніңізді растаңыз.|वर्क ऑर्डर भेजने के लिए जाँच की पुष्टि करें।|Confirm the inspection to send the work order.
dataPolicy|Как мы обрабатываем данные|Ma’lumotlarga qanday ishlov beramiz|Маълумотро чӣ тавр коркард мекунем|Маалыматты кантип иштетебиз|Деректерді қалай өңдейміз|हम डेटा कैसे संभालते हैं|How we handle data
voiceConsentTitle|Перед записью голоса|Ovoz yozishdan oldin|Пеш аз сабти овоз|Үн жаздыруудан мурун|Дауыс жазу алдында|आवाज़ रिकॉर्ड करने से पहले|Before recording your voice
voiceConsentText|Запись голоса уходит в сервис распознавания речи и не хранится. Сохраняется только текст вопроса и ответ – в журнале работы стенда.|Ovoz matnga aylantirish uchun yuboriladi va saqlanmaydi. Savol va javoblar xizmat jurnalida saqlanadi.|Овоз барои шинохтан фиристода мешавад ва нигоҳ дошта намешавад. Саволу ҷавобҳо дар дафтари хадамот нигоҳ дошта мешаванд.|Үн текстке айландыруу үчүн жөнөтүлөт жана сакталбайт. Суроолор менен жооптор кызматтын журналында сакталат.|Дауыс мәтінге айналдыру үшін жіберіледі және сақталмайды. Сұрақтар мен жауаптар сервис журналында сақталады.|आवाज़ को लिखित रूप में बदलने के लिए भेजा जाता है और रिकॉर्डिंग सहेजी नहीं जाती। सवाल और जवाब सेवा के लॉग में सहेजे जाते हैं।|Your voice is sent for transcription. The recording is not stored. Questions and answers are kept in the service log.
voiceConsentCheck|Согласен на обработку персональных данных|Shaxsiy ma’lumotlarimga ishlov berilishiga roziman|Ба коркарди маълумоти шахсӣ розӣ ҳастам|Жеке маалыматтарымды иштетүүгө макулмун|Жеке деректерімді өңдеуге келісемін|मैं अपने निजी डेटा को संसाधित करने की सहमति देता हूँ|I agree to the processing of my personal data
continueConsent|Продолжить|Davom etish|Идома додан|Улантуу|Жалғастыру|आगे बढ़ें|Continue
cancelConsent|Отмена|Bekor qilish|Бекор кардан|Жокко чыгаруу|Бас тарту|रद्द करें|Cancel
dataWhat|Что сохраняем: текст вопросов (и тот, что получен из голоса), ответы помощника и заявки.|Savollar matnini, jumladan ovozdan olingan matnni, javoblar va buyurtmalarni saqlaymiz.|Матни саволҳо, аз ҷумла матни шинохташудаи овоз, ҷавобҳо ва дархостҳоро нигоҳ медорем.|Суроолордун текстин, анын ичинде үн аркылуу алынган текстти, жоопторду жана өтүнмөлөрдү сактайбыз.|Сұрақ мәтіндерін, соның ішінде дауыстан алынған мәтінді, жауаптар мен өтінімдерді сақтаймыз.|सवालों का टेक्स्ट, आवाज़ से बना टेक्स्ट, जवाब और वर्क ऑर्डर सहेजे जाते हैं।|We keep questions, including voice transcripts, plus answers and work orders.
dataWhy|Зачем: чтобы отвечать на вопросы, оформлять заявки и вести журнал работы.|Bu savollarga javob berish, buyurtma rasmiylashtirish va ish jurnalini yuritish uchun kerak.|Ин барои посух ба саволҳо, тартиб додани дархостҳо ва пеш бурдани дафтари кор лозим аст.|Бул суроолорго жооп берүү, өтүнмө түзүү жана иш журналын жүргүзүү үчүн керек.|Бұл сұрақтарға жауап беру, өтінім рәсімдеу және жұмыс журналын жүргізу үшін қажет.|इससे सवालों के जवाब देने, वर्क ऑर्डर बनाने और काम का रिकॉर्ड रखने में मदद मिलती है।|We use this data to answer questions, create work orders and keep a service log.
dataWhere|Данные хранятся на сервере в России.|Ma’lumotlar Rossiyadagi serverda saqlanadi.|Маълумот дар сервери воқеъ дар Русия нигоҳ дошта мешавад.|Маалымат Орусиядагы серверде сакталат.|Деректер Ресейдегі серверде сақталады.|डेटा रूस में मौजूद सर्वर पर रखा जाता है।|Data is stored on a server in Russia.
dataAudio|Звук голоса отправляется в сервис распознавания речи (Google Gemini через OpenRouter) только чтобы получить текст. Ни у нас, ни в журнале он не сохраняется.|Ovoz yozuvlari saqlanmaydi. Faqat matn qoladi.|Сабтҳои овоз нигоҳ дошта намешаванд. Танҳо матн мемонад.|Үн жазуулары сакталбайт. Текст гана калат.|Дауыс жазбалары сақталмайды. Тек мәтін қалады.|आवाज़ की रिकॉर्डिंग नहीं रखी जाती। सिर्फ़ टेक्स्ट रहता है।|We do not keep voice recordings. Only the transcript is kept.
dataModels|Внешние модели (DeepSeek, Google Gemini, Jev через OpenRouter) получают текст вопроса и данные машины – без ФИО и контактов. Не пишите в вопросе личные данные.|Tashqi modellar faqat savol matni va ism-sharifsiz mashina ma’lumotlarini oladi. Savolda ism-sharif yozmang.|Моделҳои беруна танҳо матни савол ва маълумоти мошинро бе ному насаб мегиранд. Дар савол ному насаб нанависед.|Тышкы моделдер суроонун текстин жана унаа тууралуу маалыматты аты-жөнү жок алат. Суроого аты-жөндү жазбаңыз.|Сыртқы модельдер тек сұрақ мәтіні мен аты-жөні жоқ көлік деректерін алады. Сұраққа аты-жөн жазбаңыз.|बाहरी मॉडल को सिर्फ़ सवाल का टेक्स्ट और गाड़ी की जानकारी मिलती है, नाम नहीं। सवाल में किसी का पूरा नाम न लिखें।|External models get only the question text and vehicle data without names. Do not include anyone’s name in a question.
dataDemo|На демо-стенде используются вымышленные данные.|Demo stendida o‘ylab topilgan ma’lumotlar ishlatiladi.|Дар нусхаи намоишӣ маълумоти сохта истифода мешавад.|Демо нускасында ойдон чыгарылган маалымат колдонулат.|Демо нұсқасында ойдан шығарылған деректер пайдаланылады.|डेमो में काल्पनिक डेटा इस्तेमाल होता है।|The demo uses synthetic data.
openTickets|Заявок в работе|Ishdagi buyurtmalar|Дархостҳои дар иҷро|Аткарылып жаткан өтүнмөлөр|Орындалып жатқан өтінімдер|चालू वर्क ऑर्डर|Open work orders
ticketOpen|Заявка {id}|Buyurtma {id}|Дархост {id}|Өтүнмө {id}|Өтінім {id}|वर्क ऑर्डर {id}|Work order {id}
`.trim().split('\n');
  const codes = Object.keys(languages);
  const dictionary = new Map(rows.map(row => {
    const [key, ...values] = row.split('|');
    if (values.length !== codes.length || values.some(value => !value)) throw new Error(`Incomplete UI translation: ${key}`);
    return [key, values];
  }));
  const text = (lang, key, vars = {}) => (dictionary.get(key)?.[codes.indexOf(lang)] ?? key)
    .replace(/\{(\w+)\}/g, (_, name) => String(vars[name] ?? ''));
  return Object.freeze({languages, text});
})();
