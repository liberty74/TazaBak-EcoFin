import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';

export type Locale = 'RU' | 'KZ';
export type Theme = 'light' | 'dark';

export const translations = {
  RU: {
    // Navigation & Layout
    navHome: 'Главная',
    navMap: 'Карта',
    navVolunteer: 'Волонтёрство',
    navShop: 'Магазин',
    navCommunity: 'Сообщество',
    navAssistant: 'AI Баки',
    navLeaderboard: 'Рейтинг',
    navCollection: 'NFT-Коллекция',
    navSettings: 'Настройки',
    logout: 'Выйти',
    city: 'Кокшетау',
    points: 'Эко-Баллы',
    status: 'Статус',
    greeting: 'Привет, {name}!',
    subGreeting: 'Спасибо, что помогаете делать город чище.',
    demoMode: 'Демонстрационный режим',
    welcomeTitle: 'Добро пожаловать в Миску добра',
    welcomeSub: 'Выберите режим для демонстрации экосистемы',
    howToShowTitle: 'Как показать проект',
    apiConnected: 'API подключен',
    apiDisconnected: 'Ошибка подключения к API',

    // Home Page
    slogan: 'Хлеб не отход. Хлеб — помощь.',
    sloganDesc: 'Сдавайте сухой хлеб в умные контейнеры, помогайте приютам Кокшетау и получайте эко-баллы.',
    scanBread: 'Сдать хлеб',
    findBin: 'Найти контейнер',
    howItWorks: 'Как это работает',
    step1: 'Сфотографируйте хлеб',
    step1Desc: 'AI проверит его качество и содержание плесени.',
    step2: 'Получите QR-код и баллы',
    step2Desc: 'Система начислит баллы на ваш баланс.',
    step3: 'Контейнер откроется',
    step3Desc: 'Пригодный хлеб передаётся в приюты для животных.',
    socialEffect: 'Социальный эффект',
    metricBread: 'Спасено хлеба',
    metricHelped: 'Помощь приютам',
    metricActive: 'Активных участников',
    metricTasks: 'Эко-заданий',
    recentOps: 'Последние операции',
    noOps: 'У вас пока нет операций. Начните с первой сдачи хлеба.',
    newsTitle: 'Демо-новости проекта',
    newsDesc: 'Мы установили новый смарт-бак для сбора хлеба в микрорайоне Сарыарка.',

    // Profile Page
    profileTitle: 'Личный кабинет',
    roleLabel: 'Роль',
    tierLabel: 'Статус-Тир',
    pointsBalance: 'Ваш экологический баланс',
    nextTierProgress: 'Прогресс до следующего статуса',
    quickActions: 'Быстрые действия',
    addPointsBtn: 'Сдать хлеб и получить 15 баллов',
    filterAll: 'Все',
    filterIn: 'Начисления',
    filterOut: 'Покупки',
    filterNft: 'NFT',
    filterVol: 'Волонтёрство',

    // Shop Page
    shopTitle: 'Магазин Наград',
    shopSub: 'Обменивайте баллы на мерч и создавайте NFT',
    catalogTab: 'Каталог',
    mintTab: 'Создать NFT',
    noItems: 'В магазине пока нет доступных товаров',
    outOfStock: 'Нет в наличии',
    generateNftTitle: 'Создать свой Eco-NFT',
    generateNftDesc: 'NFT — это геймифицированный цифровой экологический значок. Стоимость генерации: 100 баллов.',
    nftNameLabel: 'Название для NFT',
    nftNamePlaceholder: 'Например: Спаситель Природы Кокшетау',
    mintBtn: 'Создать Eco-NFT за 100 баллов',
    mintingLoading: 'Создаём шедевр...',
    insufficientPoints: 'Недостаточно баллов',
    nftSuccess: 'Успешно!',
    nftSuccessDesc: 'Ваш новый уникальный Eco-NFT создан',
    excellentBtn: 'Отлично',

    // NFT Collection Page
    collectionTitle: 'Коллекция Eco-NFT',
    collectionSub: 'Ваши цифровые знаки экологического вклада',
    emptyCollection: 'В коллекции пока пусто. Создайте первый Eco-NFT за экологические баллы.',
    detailsBtn: 'Подробнее',
    copyIdBtn: 'Скопировать ID',
    tokenCopied: 'Token ID скопирован в буфер обмена',
    nftOwner: 'Владелец',
    nftDate: 'Дата создания',
    nftDisclaimer: 'Обратите внимание: Eco-NFT проекта «Миска добра» носят исключительно игровой и репутационный характер.',

    // Volunteer Page
    volTitle: 'Добрые дела рядом',
    volSub: 'Волонтёрские задания и помощь приютам',
    volFilterOpen: 'Открытые',
    volFilterReg: 'Участвую',
    volFilterDone: 'Завершённые',
    volRegisterBtn: 'Участвовать',
    volRegistered: 'Вы зарегистрированы',
    volReward: 'Награда',
    noTasks: 'Сейчас нет открытых инициатив.',
    pointsPendingDesc: 'Баллы будут начислены после подтверждения выполнения диспетчером.',

    // Community Page
    communityTitle: 'Сообщество',
    communitySub: 'Вместе менять город проще',
    chatPlaceholder: 'Напишите доброе сообщение...',
    sendBtn: 'Отправить',
    charLimit: 'Лимит символов',
    noMessages: 'Начните первое доброе обсуждение.',

    // Assistant Page
    assistantWelcome: 'Привет! Я Баки — экологический помощник «Миски добра». Чем могу помочь?',
    assistantSub: 'Баки помогает с вопросами проекта и экологии. Он не заменяет экстренные службы или санитарную экспертизу.',
    copyAnswer: 'Копировать ответ',
    copied: 'Ответ скопирован',
    disclaimerLabel: 'Дисклеймер',
    quickQuestion1: 'Как правильно сдать хлеб?',
    quickQuestion2: 'Где ближайший контейнер?',
    quickQuestion3: 'Как получить баллы?',
    quickQuestion4: 'Что такое Eco-NFT?',

    // Settings Page
    settingsTitle: 'Настройки приложения',
    settingsSub: 'Управление локальными параметрами',
    themeLabel: 'Тема оформления',
    themeLight: 'Светлая',
    themeDark: 'Тёмная',
    langLabel: 'Язык интерфейса',
    apiConfigLabel: 'Настройка API',
    apiDesc: 'Базовый адрес FastAPI бэкенда',
    saveBtn: 'Сохранить изменения',
    resetBtn: 'Сбросить',

    // Dispatcher
    dispatcherTitle: 'Город под контролем',
    dispatchSummary: 'Сводка диспетчера',
    dispatchBriefing: 'AI-План действий',
    unresolvedAlerts: 'Активных инцидентов',
    onlineDevices: 'Устройств онлайн',
    alertsTitle: 'Алерты системы',
    alertsSub: 'Управление инцидентами от смарт-баков',
    resolveBtn: 'Решить',
    resolveConfirm: 'Подтвердите, что инцидент обработан',
    noAlerts: 'Активных инцидентов нет. Город под контролем.',
    deviceCommandTitle: 'IoT Управление',
    deviceCommandDesc: 'Отправка команд IoT-устройствам TazaBAK',
    openLidBtn: 'Открыть крышку',
    closeLidBtn: 'Закрыть крышку',
    fireRiskActive: 'Пожарный риск всё ещё активен. Дождитесь безопасного измерения температуры.',
    commandStatusPending: 'Команда создана',
    commandStatusSent: 'Команда отправлена',
    commandStatusAcked: 'Выполнено',
    commandStatusFailed: 'Ошибка выполнения',
    dispatcherKeyModalTitle: 'Подключение диспетчерской панели',
    dispatcherKeyModalLabel: 'Локальный ключ диспетчера',
    dispatcherKeyModalDesc: 'В целях безопасности введите ключ X-Dispatcher-Key. Ввод сохраняется временно.',
    dispatcherKeyModalNote: 'В production диспетчерские запросы проходят через защищённый серверный контур.',
    dispatcherKeyModalSubmit: 'Подключить',
    briefingTitle: 'AI Сводка и план действий',
    briefingDesc: 'Рекомендации сформированы моделью Gemini',
    dispatcherKeyModalErrorEmpty: 'Пожалуйста, введите ключ',
    dispatcherKeyModalErrorNetwork: 'Ошибка подключения. Проверьте запуск API.',
    dispatcherKeyModalErrorInvalid: 'Неверный X-Dispatcher-Key. Доступ отклонен.',
    close: 'Закрыть',
    cancel: 'Отмена',
  },
  KZ: {
    // Navigation & Layout
    navHome: 'Басты бет',
    navMap: 'Карта',
    navVolunteer: 'Волонтерлік',
    navShop: 'Дүкен',
    navCommunity: 'Қауымдастық',
    navAssistant: 'AI Бәки',
    navLeaderboard: 'Рейтинг',
    navCollection: 'NFT-Коллекциясы',
    navSettings: 'Баптаулар',
    logout: 'Шығу',
    city: 'Көкшетау',
    points: 'Эко-Ұпайлар',
    status: 'Мәртебе',
    greeting: 'Сәлем, {name}!',
    subGreeting: 'Қаланы тазалауға көмектескеніңіз үшін рахмет.',
    demoMode: 'Демонстрациялық режим',
    welcomeTitle: 'Миска добра жобасына қош келдіңіз',
    welcomeSub: 'Экожүйені көрсету үшін режимді таңдаңыз',
    howToShowTitle: 'Жобаны қалай көрсету керек',
    apiConnected: 'API қосылды',
    apiDisconnected: 'API қосылу қатесі',

    // Home Page
    slogan: 'Нан қалдық емес. Нан — көмек.',
    sloganDesc: 'Құрғақ нанды ақылды контейнерлерге тапсырыңыз, Көкшетау баспаналарына көмектесіңіз және эко-ұпайлар алыңыз.',
    scanBread: 'Нан тапсыру',
    findBin: 'Бакті табу',
    howItWorks: 'Бұл қалай жұмыс істейді',
    step1: 'Нанды суретке түсіріңіз',
    step1Desc: 'AI жақсы жарықтандыруда оның сапасы мен көгеруін тексереді.',
    step2: 'QR-код пен ұпайларды алыңыз',
    step2Desc: 'Жүйе сіздің балансыңызға ұпайларды есептейді.',
    step3: 'Контейнер ашылады',
    step3Desc: 'Жарамды нан жануарларға арналған баспаналарға жіберіледі.',
    socialEffect: 'Әлеуметтік әсер',
    metricBread: 'Құтқарылған нан',
    metricHelped: 'Баспаналарға көмек',
    metricActive: 'Белсенді қатысушылар',
    metricTasks: 'Эко-тапсырмалар',
    recentOps: 'Соңғы операциялар',
    noOps: 'Сізде әлі операциялар жоқ. Алғашқы нан тапсырудан бастаңыз.',
    newsTitle: 'Жобаның демо-жаңалықтары',
    newsDesc: 'Сарыарқа шағын ауданында нан жинауға арналған жаңа смарт-бак орнаттық.',

    // Profile Page
    profileTitle: 'Жеке кабинет',
    roleLabel: 'Рөл',
    tierLabel: 'Мәртебе-Деңгей',
    pointsBalance: 'Сіздің экологиялық балансыңыз',
    nextTierProgress: 'Келесі мәртебеге дейінгі прогресс',
    quickActions: 'Жылдам әрекеттер',
    addPointsBtn: 'Нан тапсырып, 15 ұпай алу',
    filterAll: 'Барлығы',
    filterIn: 'Есептеулер',
    filterOut: 'Сатып алулар',
    filterNft: 'NFT',
    filterVol: 'Волонтерлік',

    // Shop Page
    shopTitle: 'Сыйлықтар Дүкені',
    shopSub: 'Ұпайларды мерчқа алмастырыңыз және NFT жасаңыз',
    catalogTab: 'Каталог',
    mintTab: 'NFT жасау',
    noItems: 'Дүкенде әлі қолжетімді тауарлар жоқ',
    outOfStock: 'Қоймада жоқ',
    generateNftTitle: 'Өз Eco-NFT-іңізді жасаңыз',
    generateNftDesc: 'NFT — бұл ойын түріндегі цифрлық экологиялық белгі. Жасау құны: 100 ұпай.',
    nftNameLabel: 'NFT атауы',
    nftNamePlaceholder: 'Мысалы: Көкшетау Табиғат Құтқарушысы',
    mintBtn: '100 ұпайға Eco-NFT жасау',
    mintingLoading: 'Туынды жасаудамыз...',
    insufficientPoints: 'Ұпайлар жеткіліксіз',
    nftSuccess: 'Сәтті жасалды!',
    nftSuccessDesc: 'Сіздің жаңа бірегей Eco-NFT жасалды',
    excellentBtn: 'Тамаша',

    // NFT Collection Page
    collectionTitle: 'Eco-NFT Коллекциясы',
    collectionSub: 'Сіздің экологиялық үлесіңіздің цифрлық белгілері',
    emptyCollection: 'Коллекция әлі бос. Эко-ұпайларға алғашқы Eco-NFT жасаңыз.',
    detailsBtn: 'Толығырақ',
    copyIdBtn: 'ID көшіру',
    tokenCopied: 'Token ID алмасу буферіне көшірілді',
    nftOwner: 'Иесі',
    nftDate: 'Жасалған күні',
    nftDisclaimer: 'Назар аударыңыз: «Миска добра» жобасының Eco-NFT-тері тек ойын және бедел сипатына ие.',

    // Volunteer Page
    volTitle: 'Жақын маңдағы игі істер',
    volSub: 'Волонтерлік тапсырмалар және баспаналарға көмек',
    volFilterOpen: 'Ашық',
    volFilterReg: 'Қатысамын',
    volFilterDone: 'Аяқталған',
    volRegisterBtn: 'Қатысу',
    volRegistered: 'Сіз тіркелдіңіз',
    volReward: 'Сыйақы',
    noTasks: 'Қазіргі уақытта ашық бастамалар жоқ.',
    pointsPendingDesc: 'Ұпайлар диспетчер орындалуын растағаннан кейін есептеледі.',

    // Community Page
    communityTitle: 'Қауымдастық',
    communitySub: 'Қаланы бірге өзгерту оңайырақ',
    chatPlaceholder: 'Жылы хабарлама жазыңыз...',
    sendBtn: 'Жіберу',
    charLimit: 'Таңбалар шегі',
    noMessages: 'Алғашқы игі талқылауды бастаңыз.',

    // Assistant Page
    assistantWelcome: 'Сәлем! Мен Бәкимін — «Миска добра» жобасының экологиялық көмекшісімін. Қалай көмектесе аламын?',
    assistantSub: 'Бәки жоба және экология сұрақтары бойынша көмектеседі. Ол шұғыл қызметтерді немесе санитарлық сараптаманы алмастырмайды.',
    copyAnswer: 'Жауапты көшіру',
    copied: 'Жауап көшірілді',
    disclaimerLabel: 'Жауапкершіліктен бас тарту',
    quickQuestion1: 'Нанды қалай дұрыс тапсыруға болады?',
    quickQuestion2: 'Ең жақын контейнер қайда орналасқан?',
    quickQuestion3: 'Ұпайларды қалай алуға болады?',
    quickQuestion4: 'Eco-NFT дегеніміз не?',

    // Settings Page
    settingsTitle: 'Қосымша баптаулары',
    settingsSub: 'Жергілікті параметрлерді басқару',
    themeLabel: 'Рәсімдеу тақырыбы',
    themeLight: 'Жарық',
    themeDark: 'Қараңғы',
    langLabel: 'Интерфейс тілі',
    apiConfigLabel: 'API баптаулары',
    apiDesc: 'FastAPI бэкендінің базалық мекенжайы',
    saveBtn: 'Өзгерістерді сақтау',
    resetBtn: 'Қалпына келтіру',

    // Dispatcher
    dispatcherTitle: 'Қала бақылауда',
    dispatchSummary: 'Диспетчер жиынтығы',
    dispatchBriefing: 'AI-Іс-қимыл жоспары',
    unresolvedAlerts: 'Белсенді оқиғалар',
    onlineDevices: 'Қосулы құрылғылар',
    alertsTitle: 'Жүйелік алерттер',
    alertsSub: 'Смарт-бактерден келетін оқиғаларды басқару',
    resolveBtn: 'Шешу',
    resolveConfirm: 'Оқиғаның өңделгенін растаңыз',
    noAlerts: 'Белсенді оқиғалар жоқ. Қала бақылауда.',
    deviceCommandTitle: 'IoT Басқару',
    deviceCommandDesc: 'TazaBAK IoT құрылғыларына командалар жіберу',
    openLidBtn: 'Қақпақты ашу',
    closeLidBtn: 'Қақпақты жабу',
    fireRiskActive: 'Өрт қаупі әлі де белсенді. Температураның қауіпсіз өлшемін күтіңіз.',
    commandStatusPending: 'Команда жасалды',
    commandStatusSent: 'Команда жіберілді',
    commandStatusAcked: 'Орындалды',
    commandStatusFailed: 'Орындау қатесі',
    dispatcherKeyModalTitle: 'Диспетчерлік панельді қосу',
    dispatcherKeyModalLabel: 'Диспетчердің жергілікті кілті',
    dispatcherKeyModalDesc: 'Қауіпсіздік мақсатында X-Dispatcher-Key кілтін енгізіңіз. Енгізу уақытша сақталады.',
    dispatcherKeyModalNote: 'Production режимінде диспетчерлік сұраныстар қорғалған серверлік контур арқылы өтеді.',
    dispatcherKeyModalSubmit: 'Қосу',
    briefingTitle: 'AI Жиынтығы және іс-қимыл жоспары',
    briefingDesc: 'Ұсыныстар Gemini моделімен әзірленген',
    dispatcherKeyModalErrorEmpty: 'Кілтті енгізіңіз',
    dispatcherKeyModalErrorNetwork: 'Қосылу қатесі. API іске қосылуын тексеріңіз.',
    dispatcherKeyModalErrorInvalid: 'Қате X-Dispatcher-Key. Рұқсат берілмеді.',
    close: 'Жабу',
    cancel: 'Бас тарту',
  },
};

interface LocaleThemeContextType {
  locale: Locale;
  theme: Theme;
  setLocale: (locale: Locale) => void;
  setTheme: (theme: Theme) => void;
  toggleLocale: () => void;
  toggleTheme: () => void;
  t: (key: keyof typeof translations['RU']) => string;
}

const LocaleThemeContext = createContext<LocaleThemeContextType | undefined>(undefined);

export const LocaleThemeProvider = ({ children }: { children: ReactNode }) => {
  const [locale, setLocaleState] = useState<Locale>(() => {
    const saved = localStorage.getItem('appLocale');
    if (saved === 'RU' || saved === 'KZ') return saved;
    return 'RU';
  });

  const [theme, setThemeState] = useState<Theme>(() => {
    const saved = localStorage.getItem('appTheme');
    if (saved === 'light' || saved === 'dark') return saved;
    return 'light';
  });

  const setLocale = (newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem('appLocale', newLocale);
  };

  const setTheme = (newTheme: Theme) => {
    setThemeState(newTheme);
    localStorage.setItem('appTheme', newTheme);
  };

  const toggleLocale = () => {
    setLocale(locale === 'RU' ? 'KZ' : 'RU');
  };

  const toggleTheme = () => {
    setTheme(theme === 'light' ? 'dark' : 'light');
  };

  useEffect(() => {
    const root = window.document.documentElement;
    root.classList.remove('light', 'dark');
    root.classList.add(theme);
  }, [theme]);

  const t = (key: keyof typeof translations['RU']): string => {
    return translations[locale][key] || translations['RU'][key] || String(key);
  };

  return (
    <LocaleThemeContext.Provider value={{ locale, theme, setLocale, setTheme, toggleLocale, toggleTheme, t }}>
      {children}
    </LocaleThemeContext.Provider>
  );
};

export const useLocaleTheme = () => {
  const context = useContext(LocaleThemeContext);
  if (context === undefined) {
    throw new Error('useLocaleTheme must be used within a LocaleThemeProvider');
  }
  return context;
};
