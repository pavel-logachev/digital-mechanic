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
fleet|Сводка парка|Avtopark holati|Ҳолати автопарк|Автопарктын абалы|Автопарк күйі|बेड़े की स्थिति|Fleet overview
vehicle|Карточка машины|Mashina kartasi|Маълумоти мошин|Унаа тууралуу|Көлік картасы|गाड़ी की जानकारी|Vehicle details
chat|Диагностика|Diagnostika|Ташхис|Диагностика|Диагностика|जाँच का नतीजा|Diagnosis
draft|Черновик заявки|Buyurtma qoralamasi|Пешнависи дархост|Өтүнмөнүн долбоору|Өтінім жобасы|वर्क ऑर्डर का मसौदा|Work order draft
receipt|Заявка создана|Buyurtma ochildi|Дархост сабт шуд|Өтүнмө түзүлдү|Өтінім жасалды|वर्क ऑर्डर बन गया|Work order created
choose|Выберите машину|Mashinani tanlang|Мошинро интихоб кунед|Унааны тандаңыз|Көлікті таңдаңыз|गाड़ी चुनें|Choose a vehicle
search|Госномер или гаражный №|Davlat yoki garaj raqami|Рақами давлатӣ ё гаражӣ|Мамлекеттик же гараж номери|Мемлекеттік не гараж нөмірі|रजिस्ट्रेशन या गैराज नंबर|Plate or garage number
numberKeys|Клавиатура: цифры|Raqamli klaviatura|Клавиатураи рақамӣ|Сан баскычтары|Сандық пернетақта|अंकों का कीबोर्ड|Number keypad
textKeys|Клавиатура: буквы и цифры|Harf va raqam klaviaturasi|Клавиатураи ҳарфу рақам|Тамга жана сан баскычтары|Әріп пен сан пернетақтасы|अक्षर और अंक का कीबोर्ड|Letters and numbers
clear|Очистить поиск|Qidiruvni tozalash|Тоза кардани ҷустуҷӯ|Издөөнү тазалоо|Іздеуді тазалау|खोज मिटाएँ|Clear search
vehicleList|Машины|Mashinalar|Мошинҳо|Унаалар|Көліктер|गाड़ियाँ|Vehicles
count|{found} из {total}|{found} / {total}|{found} аз {total}|{total} ичинен {found}|{total} ішінен {found}|{total} में से {found}|{found} of {total}
noResults|Машин с таким номером нет|Bunday raqamli mashina yo‘q|Бо ин рақам мошин ёфт нашуд|Мындай номерлүү унаа жок|Мұндай нөмірлі көлік жоқ|इस नंबर की गाड़ी नहीं मिली|No vehicles match this number
showAll|Показать все ({count})|Hammasini ko‘rsatish ({count})|Ҳамаро нишон диҳед ({count})|Баарын көрсөтүү ({count})|Бәрін көрсету ({count})|सभी दिखाएँ ({count})|Show all ({count})
garage|Гаражный № {no}|Garaj raqami {no}|Рақами гаражӣ {no}|Гараж номери {no}|Гараж нөмірі {no}|गैराज नं. {no}|Garage no. {no}
normal|Норма|Me’yorda|Дар меъёр|Нормада|Қалыпты|सामान्य|Normal
anomaly|Отклонение|Og‘ish bor|Инҳироф|Четтөө бар|Ауытқу бар|गड़बड़ी का संकेत|Anomaly
failed|Плохая запись|Yozuv sifatsiz|Сабти пастсифат|Жазуу сапатсыз|Жазба сапасыз|रिकॉर्डिंग खराब है|Poor recording
noCheck|Нет проверки|Tekshiruv yo‘q|Санҷиш нашудааст|Текшерүү жок|Тексеру жоқ|जाँच नहीं हुई|No check
attention|Нужна проверка|Tekshirish kerak|Санҷидан лозим|Текшерүү керек|Тексеру керек|जाँच ज़रूरी है|Needs attention
quarantine|Карантин|Karantinda|Дар карантин|Карантинде|Карантинде|सेवा से बाहर|Quarantined
fleetPriority|Машины, требующие внимания|Tekshirish kerak bo‘lgan mashinalar|Мошинҳое, ки бояд санҷид|Текшериле турган унаалар|Тексеру керек көліктер|जिन गाड़ियों की जाँच चाहिए|Vehicles needing attention
fleetEmpty|Все машины в норме|Hamma mashina me’yorda|Ҳамаи мошинҳо дар меъёр|Бардык унаа нормада|Барлық көлік қалыпты|सभी गाड़ियाँ सामान्य हैं|All vehicles are normal
engine|Двигатель|Dvigatel|Муҳаррик|Кыймылдаткыч|Қозғалтқыш|इंजन|Engine
checks|История проверок|Tekshiruvlar tarixi|Санҷишҳои гузашта|Мурунку текшерүүлөр|Бұрынғы тексерулер|पिछली जाँचें|Check history
lastCheck|Последняя проверка|Oxirgi tekshiruv|Санҷиши охирин|Акыркы текшерүү|Соңғы тексеру|आखिरी जाँच|Latest check
chooseCheck|Выберите проверку|Tekshiruvni tanlang|Санҷишро интихоб кунед|Текшерүүнү тандаңыз|Тексеруді таңдаңыз|जाँच चुनें|Choose a check
noChecks|Проверок пока нет|Hozircha tekshiruv yo‘q|Ҳоло санҷиш нест|Азырынча текшерүү жок|Әзірге тексеру жоқ|अभी कोई जाँच नहीं है|No checks yet
score|Оценка отклонения|Og‘ish balli|Баҳои инҳироф|Четтөө баасы|Ауытқу бағасы|गड़बड़ी का स्कोर|Anomaly score
noScore|Нет оценки|Ball yo‘q|Баҳо нест|Баа жок|Баға жоқ|कोई स्कोर नहीं|No score
trendNote|Шкала от 0 до 1. × – запись не подошла. Сравнивайте только записи, сделанные в одинаковых условиях.|Shkala 0 dan 1 gacha. × – yozuv yaroqsiz. Faqat bir xil sharoitda olingan yozuvlarni solishtiring.|Миқёс аз 0 то 1. × – сабт корношоям аст. Танҳо сабтҳои дар шароити яксон гирифташударо муқоиса кунед.|Шкала 0дөн 1ге чейин. × – жазуу жараксыз. Бирдей шартта жасалган жазууларды гана салыштырыңыз.|Шкала 0-ден 1-ге дейін. × – жазба жарамсыз. Тек бірдей жағдайда жазылған дыбыстарды салыстырыңыз.|स्कोर 0 से 1 तक है। × – रिकॉर्डिंग काम की नहीं है। एक जैसे हालात में की गई रिकॉर्डिंग ही मिलाएँ।|Scale: 0 to 1. × means the recording was unusable. Only compare recordings made under the same conditions.
pastTickets|Прошлые заявки|Oldingi buyurtmalar|Дархостҳои гузашта|Мурунку өтүнмөлөр|Бұрынғы өтінімдер|पिछले वर्क ऑर्डर|Past work orders
noTickets|Заявок пока нет|Hozircha buyurtma yo‘q|Ҳоло дархост нест|Азырынча өтүнмө жок|Әзірге өтінім жоқ|अभी कोई वर्क ऑर्डर नहीं है|No work orders yet
diagnose|Показать результат|Natijani ko‘rsatish|Нишон додани натиҷа|Жыйынтыкты көрүү|Нәтижені көру|नतीजा देखें|Show result
loading|Загружаем данные…|Ma’lumot yuklanmoqda…|Маълумот бор мешавад…|Маалымат жүктөлүүдө…|Дерек жүктелуде…|जानकारी आ रही है…|Loading…
loadFailed|Не удалось загрузить данные|Ma’lumot yuklanmadi|Маълумот бор нашуд|Маалымат жүктөлгөн жок|Дерек жүктелмеді|जानकारी नहीं आ सकी|Could not load data
retry|Повторить|Qayta urinish|Аз нав кӯшиш кунед|Кайра аракет кылуу|Қайталау|फिर कोशिश करें|Try again
serviceError|Ошибка сервиса ({code})|Xizmat xatosi ({code})|Хатои хидмат ({code})|Кызмат катасы ({code})|Қызмет қатесі ({code})|सेवा में गड़बड़ी ({code})|Service error ({code})
network|Нет связи. Проверьте интернет и попробуйте снова.|Aloqa yo‘q. Internetni tekshirib, qayta urinib ko‘ring.|Пайваст нест. Интернетро санҷеду аз нав кӯшиш кунед.|Байланыш жок. Интернетти текшерип, кайра аракет кылыңыз.|Байланыс жоқ. Интернетті тексеріп, қайта көріңіз.|कनेक्शन नहीं है। इंटरनेट जाँचकर फिर कोशिश करें।|No connection. Check your internet and try again.
normalTitle|Отклонений не выявлено|Og‘ish topilmadi|Инҳироф ёфт нашуд|Четтөө табылган жок|Ауытқу табылмады|कोई गड़बड़ी नहीं मिली|No anomaly found
anomalyTitle|Есть признаки отклонения|Og‘ish belgilari bor|Нишонаҳои инҳироф ҳастанд|Четтөөнүн белгилери бар|Ауытқу белгілері бар|गड़बड़ी के संकेत मिले|Signs of an anomaly
notApplicable|Тип отклонения не подтвержден|Og‘ish turi tasdiqlanmadi|Навъи инҳироф тасдиқ нашуд|Четтөөнүн түрү ырасталган жок|Ауытқу түрі расталмады|गड़बड़ी की वजह पक्की नहीं है|Anomaly type not confirmed
hypothesis|Гипотеза: {name}|Taxmin: {name}|Тахмин: {name}|Божомол: {name}|Болжам: {name}|संभावित खराबी: {name}|Possible fault: {name}
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
metrics|Данные проверки|Tekshiruv ma’lumotlari|Маълумоти санҷиш|Текшерүү маалыматы|Тексеру дерегі|जाँच का विवरण|Check details
confidence|Уверенность модели|Model ishonchi|Эътимоди модел|Моделдин ишеними|Модель сенімділігі|मॉडल का भरोसा|Model confidence
quality|Качество записи|Yozuv sifati|Сифати сабт|Жазуунун сапаты|Жазба сапасы|रिकॉर्डिंग की गुणवत्ता|Recording quality
good|Хорошее|Yaxshi|Хуб|Жакшы|Жақсы|अच्छी|Good
noisy|С помехами|Shovqinli|Бо халал|Ызы-чуу бар|Шулы|शोर है|Noisy
poor|Плохое|Yomon|Паст|Начар|Нашар|खराब|Poor
noData|Нет данных|Ma’lumot yo‘q|Маълумот нест|Маалымат жок|Дерек жоқ|जानकारी नहीं|No data
sources|Источники|Manbalar|Манбаъҳо|Булактар|Дереккөздер|स्रोत|Sources
source|Источник {n}: {name}, страница {page}|Manba {n}: {name}, {page}-bet|Манбаи {n}: {name}, саҳифаи {page}|Булак {n}: {name}, {page}-бет|Дереккөз {n}: {name}, {page}-бет|स्रोत {n}: {name}, पन्ना {page}|Source {n}: {name}, page {page}
pageRef|{name}, стр. {page}|{name}, {page}-bet|{name}, саҳ. {page}|{name}, {page}-бет|{name}, {page}-бет|{name}, पन्ना {page}|{name}, p. {page}
steps|Ход проверки|Tekshiruv bosqichlari|Рафти санҷиш|Текшерүүнүн жүрүшү|Тексеру барысы|जाँच के चरण|Progress log
working|В работе|Bajarilmoqda|Дар кор|Аткарылууда|Орындалуда|काम जारी है|In progress
error|Ошибка|Xato|Хато|Ката|Қате|गड़बड़ी|Error
done|Готово|Tayyor|Тайёр|Даяр|Дайын|हो गया|Done
mechanic|Вы|Siz|Шумо|Сиз|Сіз|आप|You
answer|Ответ механика|Mexanik javobi|Ҷавоби механик|Механиктин жообу|Механик жауабы|मैकेनिक का जवाब|Mechanic’s answer
result|Результат проверки|Tekshiruv natijasi|Натиҷаи санҷиш|Текшерүү жыйынтыгы|Тексеру нәтижесі|जाँच का नतीजा|Check result
pending|Готовлю ответ…|Javob tayyorlayapman…|Ҷавобро тайёр мекунам…|Жооп даярдап жатам…|Жауап дайындап жатырмын…|जवाब तैयार हो रहा है…|Preparing an answer…
stepDiagnose|Проверяю запись…|Yozuvni tekshiryapman…|Сабтро месанҷам…|Жазууну текшерип жатам…|Жазбаны тексеріп жатырмын…|रिकॉर्डिंग की जाँच हो रही है…|Checking the recording…
stepHistory|Смотрю историю машины…|Mashina tarixini ko‘ryapman…|Санҷишҳои гузаштаро мебинам…|Унаанын тарыхын карап жатам…|Көлік тарихын қарап жатырмын…|गाड़ी की पिछली जाँचें देख रहे हैं…|Checking vehicle history…
stepSearch|Ищу в руководстве…|Qo‘llanmadan izlayapman…|Дар дастур меҷӯям…|Колдонмодон издеп жатам…|Нұсқаулықтан іздеп жатырмын…|मैनुअल में ढूँढ रहे हैं…|Searching the manual…
stepRead|Читаю страницу руководства…|Qo‘llanma betini o‘qiyapman…|Саҳифаи дастурро мехонам…|Колдонмонун бетин окуп жатам…|Нұсқаулық бетін оқып жатырмын…|मैनुअल का पन्ना पढ़ रहे हैं…|Reading the manual…
stepFault|Уточняю тип отклонения…|Og‘ish turini aniqlayapman…|Навъи инҳирофро месанҷам…|Четтөөнүн түрүн тактап жатам…|Ауытқу түрін анықтап жатырмын…|गड़बड़ी की वजह देख रहे हैं…|Checking the possible fault…
stepDraft|Готовлю черновик…|Qoralama tayyorlayapman…|Пешнавис месозам…|Өтүнмөнүн долбоорун даярдап жатам…|Өтінім жобасын дайындап жатырмын…|मसौदा तैयार हो रहा है…|Preparing a draft…
openReceipt|Открыть квитанцию|Kvitansiyani ochish|Кушодани расид|Дүмүрчөктү ачуу|Түбіртекті ашу|रसीद खोलें|Open receipt
createDraft|Подготовить заявку|Buyurtma tayyorlash|Тайёр кардани дархост|Өтүнмө даярдоо|Өтінім дайындау|वर्क ऑर्डर तैयार करें|Prepare work order
openDraft|Открыть черновик|Qoralamani ochish|Кушодани пешнавис|Долбоорду ачуу|Жобаны ашу|मसौदा खोलें|Open draft
question|Напишите вопрос|Savol yozing|Савол нависед|Суроо жазыңыз|Сұрақ жазыңыз|सवाल लिखें|Type a question
send|Отправить|Yuborish|Фиристодан|Жөнөтүү|Жіберу|भेजें|Send
sendQuestion|Отправить вопрос|Savolni yuborish|Фиристодани савол|Суроону жөнөтүү|Сұрақты жіберу|सवाल भेजें|Send question
mic|Продиктовать вопрос|Savolni ovoz bilan aytish|Бо овоз савол додан|Суроону үн менен айтуу|Сұрақты дауыспен айту|बोलकर सवाल पूछें|Dictate a question
micShort|Голосом|Ovoz|Бо овоз|Үн менен|Дауыспен|बोलें|Speak
micStop|Остановить запись|Yozuvni to‘xtatish|Қатъи сабт|Жазууну токтотуу|Жазуды тоқтату|रिकॉर्डिंग रोकें|Stop recording
micAsk|Запрашиваем доступ к микрофону…|Mikrofonga ruxsat so‘ralmoqda…|Дастрасӣ ба микрофонро мепурсем…|Микрофонго уруксат суралууда…|Микрофонға рұқсат сұралуда…|माइक की अनुमति माँग रहे हैं…|Requesting microphone access…
micRecording|Идет запись|Ovoz yozilmoqda|Сабт идома дорад|Үн жазылууда|Дыбыс жазылуда|रिकॉर्डिंग चालू है|Recording
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
confirm|Подтвердить и отправить|Tasdiqlash va yuborish|Тасдиқ ва фиристодан|Ырастап жөнөтүү|Растап жіберу|पक्का करके भेजें|Confirm and send
confirmNote|Заявка уйдет в ТОиР.|Buyurtma texnik xizmat tizimiga yuboriladi.|Дархост ба низоми таъмир меравад.|Өтүнмө тейлөө тутумуна жөнөтүлөт.|Өтінім жөндеу жүйесіне жіберіледі.|वर्क ऑर्डर रखरखाव सिस्टम में जाएगा।|This sends the order to the maintenance system.
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
pageNumber|Стр. {page} / {total}|{page} / {total}-bet|Саҳ. {page} / {total}|{page} / {total}-бет|{page} / {total}-бет|पन्ना {page} / {total}|Page {page} / {total}
pageText|Текст страницы|Bet matni|Матни саҳифа|Беттин тексти|Бет мәтіні|पन्ने का पाठ|Page text
quote|Цитата из ответа|Javobdagi iqtibos|Иқтибос аз ҷавоб|Жооптон үзүндү|Жауаптан дәйексөз|जवाब में दिया अंश|Quote from answer
pageUnavailable|Страница недоступна|Bet ochilmadi|Саҳифа дастрас нест|Бет жеткиликсиз|Бет қолжетімсіз|पन्ना नहीं खुला|Page unavailable
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
