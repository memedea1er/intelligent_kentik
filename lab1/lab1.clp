;; ИНСТРУКЦИЯ ПО ЗАПУСКУ:
;; ----------------------
;; 1. Запустить CLIPS
;; 2. Выполнить команды в следующей последовательности:
;;    CLIPS> (clear)
;;    CLIPS> (load "games.clp")
;;    CLIPS> (reset)     ; Команда reset подставляет факты из deffacts
;;    CLIPS> (run)

;; ============================================================================
;; РАЗДЕЛ 1: ОПРЕДЕЛЕНИЕ ШАБЛОНОВ (DEFTEMPLATES)
;; ============================================================================

(deftemplate user-input
  "Структура для хранения всех ответов пользователя"
  (slot has-pc           (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot has-playstation  (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot has-xbox         (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot likes-action     (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot likes-rpg        (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot likes-strategy   (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot likes-simulators (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot likes-adventure  (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot has-online       (type SYMBOL) (default nil) (allowed-symbols да нет nil))
  (slot short-sessions   (type SYMBOL) (default nil) (allowed-symbols да нет nil)))

;; ============================================================================
;; РАЗДЕЛ 2: НАЧАЛЬНЫЕ ФАКТЫ (DEFFACTS)
;; ============================================================================

(deffacts startup
  "Начальные факты для запуска системы после команды (reset)"
  (stage awaiting-input)
  (system-ready))

;; ============================================================================
;; РАЗДЕЛ 3: ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ (DEFFUNCTIONS)
;; ============================================================================

(deffunction ask-yes-no (?question)
  "Запрашивает у пользователя ответ да или нет и проверяет корректность"
  (printout t ?question " (да/нет): ")
  (bind ?input (read))
  (while (and (neq ?input да) (neq ?input нет))
    (printout t "Ошибка! Введите 'да' или 'нет'." crlf)
    (printout t ?question " (да/нет): ")
    (bind ?input (read)))
  (return ?input))

;; ============================================================================
;; РАЗДЕЛ 4: ПРАВИЛА ИНИЦИАЛИЗАЦИИ И ОПРОСА
;; ============================================================================

(defrule init-questions
  "Запускает процесс опроса пользователя при старте системы"
  (declare (salience 100))
  ?stage-fact <- (stage awaiting-input)
  (system-ready)
  =>
  (printout t crlf)
  (printout t "========================================" crlf)
  (printout t "СИСТЕМА РЕКОМЕНДАЦИЙ ВИДЕОИГР" crlf)
  (printout t "========================================" crlf)
  (printout t crlf)
  
  ;; Опрос о платформах
  (bind ?pc (ask-yes-no "Есть ли у вас ПК?"))
  (bind ?ps (ask-yes-no "Есть ли у вас Playstation?"))
  (bind ?xbox (ask-yes-no "Есть ли у вас Xbox?"))
  
  ;; Опрос о жанровых предпочтениях
  (bind ?action (ask-yes-no "Нравятся ли вам экшены?"))
  (bind ?rpg (ask-yes-no "Нравятся ли вам RPG?"))
  (bind ?strategy (ask-yes-no "Нравятся ли вам стратегии?"))
  (bind ?simulators (ask-yes-no "Нравятся ли вам симуляторы?"))
  (bind ?adventure (ask-yes-no "Нравятся ли вам приключения?"))
  
  ;; Опрос о дополнительных условиях
  (bind ?online (ask-yes-no "Есть ли у вас доступ к онлайн-режиму?"))
  (bind ?short (ask-yes-no "Вы предпочитаете короткие игровые сессии?"))
  
  ;; Сохранение всех ответов
  (assert (user-input
    (has-pc ?pc)
    (has-playstation ?ps)
    (has-xbox ?xbox)
    (likes-action ?action)
    (likes-rpg ?rpg)
    (likes-strategy ?strategy)
    (likes-simulators ?simulators)
    (likes-adventure ?adventure)
    (has-online ?online)
    (short-sessions ?short)))
  
  ;; Переход к фазе вывода
  (retract ?stage-fact)
  (assert (stage inference))
  (printout t crlf "Анализируем ваши предпочтения..." crlf crlf))

;; ============================================================================
;; РАЗДЕЛ 5: ПРАВИЛА ОПРЕДЕЛЕНИЯ ПЛАТФОРМЫ (ПРАВИЛА 1-3)
;; ============================================================================

(defrule rule-01-platform-pc
  "Если есть ПК, то платформа = ПК"
  (stage inference)
  (user-input (has-pc да))
  (not (platform ?))
  =>
  (assert (platform ПК))
  (printout t "[Правило 1] Есть ПК => платформа = ПК" crlf))

(defrule rule-02-platform-console
  "Если есть Playstation или Xbox, то платформа = консоль"
  (stage inference)
  (or
    (user-input (has-playstation да))
    (user-input (has-xbox да))
  )
  (not (platform ?))
  =>
  (assert (platform консоль))
  (printout t "[Правило 2] Есть Playstation или Xbox => платформа = консоль" crlf))

(defrule rule-03-no-platform
  "Если нет никакой платформы"
  (stage inference)
  (user-input (has-pc нет) (has-playstation нет) (has-xbox нет))
  (not (no-platform да))
  =>
  (assert (no-platform да))
  (printout t "[Правило 3] Нет доступных платформ => не можем подобрать игру" crlf))

;; ============================================================================
;; РАЗДЕЛ 6: ПРАВИЛА ОПРЕДЕЛЕНИЯ ДОСТУПНЫХ ЖАНРОВ (ПРАВИЛА 4-9)
;; ============================================================================

(defrule rule-04-action-available
  "Если нравятся экшены, то экшены доступны"
  (stage inference)
  (user-input (likes-action да))
  (not (genre-available экшен))
  =>
  (assert (genre-available экшен))
  (printout t "[Правило 4] Нравятся экшены => экшены доступны" crlf))

(defrule rule-05-rpg-available
  "Если нравятся RPG, то RPG доступны"
  (stage inference)
  (user-input (likes-rpg да))
  (not (genre-available rpg))
  =>
  (assert (genre-available rpg))
  (printout t "[Правило 5] Нравятся RPG => RPG доступны" crlf))

(defrule rule-06-strategy-available-from-strategy
  "Если нравятся стратегии, то стратегии доступны"
  (stage inference)
  (user-input (likes-strategy да))
  (not (genre-available стратегия))
  =>
  (assert (genre-available стратегия))
  (printout t "[Правило 6] Нравятся стратегии => стратегии доступны" crlf))

(defrule rule-07-strategy-available-from-simulators
  "Если нравятся симуляторы, то стратегии доступны"
  (stage inference)
  (user-input (likes-simulators да))
  (not (genre-available стратегия))
  =>
  (assert (genre-available стратегия))
  (printout t "[Правило 7] Нравятся симуляторы => стратегии доступны" crlf))

(defrule rule-08-adventure-available
  "Если нравятся приключения и есть онлайн, то приключения доступны"
  (stage inference)
  (user-input (likes-adventure да) (has-online да))
  (not (genre-available приключение))
  =>
  (assert (genre-available приключение))
  (printout t "[Правило 8] Нравятся приключения + есть онлайн => приключения доступны" crlf))

(defrule rule-09-adventure-not-available
  "Если нравятся приключения, но нет онлайна"
  (stage inference)
  (user-input (likes-adventure да) (has-online нет))
  (not (adventure-not-available да))
  =>
  (assert (adventure-not-available да))
  (printout t "[Правило 9] Нравятся приключения, но нет онлайна => приключения недоступны" crlf))

;; ============================================================================
;; РАЗДЕЛ 7: ПРАВИЛА КОМБИНИРОВАНИЯ ПЛАТФОРМЫ И ЖАНРОВ (ПРАВИЛА 10-17)
;; ============================================================================

(defrule rule-10-action-pc
  "ПК + экшены = экшены для ПК доступны"
  (stage inference)
  (platform ПК)
  (genre-available экшен)
  (not (action-pc да))
  =>
  (assert (action-pc да))
  (printout t "[Правило 10] ПК + экшены => экшены для ПК доступны" crlf))

(defrule rule-11-action-console
  "Консоль + экшены = экшены для консолей доступны"
  (stage inference)
  (platform консоль)
  (genre-available экшен)
  (not (action-console да))
  =>
  (assert (action-console да))
  (printout t "[Правило 11] Консоль + экшены => экшены для консолей доступны" crlf))

(defrule rule-12-rpg-pc
  "ПК + RPG = RPG для ПК доступны"
  (stage inference)
  (platform ПК)
  (genre-available rpg)
  (not (rpg-pc да))
  =>
  (assert (rpg-pc да))
  (printout t "[Правило 12] ПК + RPG => RPG для ПК доступны" crlf))

(defrule rule-13-rpg-console
  "Консоль + RPG = RPG для консолей доступны"
  (stage inference)
  (platform консоль)
  (genre-available rpg)
  (not (rpg-console да))
  =>
  (assert (rpg-console да))
  (printout t "[Правило 13] Консоль + RPG => RPG для консолей доступны" crlf))

(defrule rule-14-strategy-pc
  "ПК + стратегии = стратегии для ПК доступны"
  (stage inference)
  (platform ПК)
  (genre-available стратегия)
  (not (strategy-pc да))
  =>
  (assert (strategy-pc да))
  (printout t "[Правило 14] ПК + стратегии => стратегии для ПК доступны" crlf))

(defrule rule-15-strategy-console
  "Консоль + стратегии = стратегии для консолей доступны"
  (stage inference)
  (platform консоль)
  (genre-available стратегия)
  (not (strategy-console да))
  =>
  (assert (strategy-console да))
  (printout t "[Правило 15] Консоль + стратегии => стратегии для консолей доступны" crlf))

(defrule rule-16-adventure-pc
  "ПК + приключения = приключения для ПК доступны"
  (stage inference)
  (platform ПК)
  (genre-available приключение)
  (not (adventure-pc да))
  =>
  (assert (adventure-pc да))
  (printout t "[Правило 16] ПК + приключения => приключения для ПК доступны" crlf))

(defrule rule-17-adventure-console
  "Консоль + приключения = приключения для консолей доступны"
  (stage inference)
  (platform консоль)
  (genre-available приключение)
  (not (adventure-console да))
  =>
  (assert (adventure-console да))
  (printout t "[Правило 17] Консоль + приключения => приключения для консолей доступны" crlf))

;; ============================================================================
;; РАЗДЕЛ 8: ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ С УЧЕТОМ СЕССИЙ (ПРАВИЛА 18-30)
;; ============================================================================

;; Экшены для ПК
(defrule rule-18-action-pc-short
  "Экшены для ПК + короткие сессии = Counter Strike"
  (declare (salience 10))
  (stage inference)
  (action-pc да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Counter-Strike))
  (printout t "[Правило 18] Экшены для ПК + короткие сессии => Counter-Strike" crlf))

(defrule rule-19-action-pc-long
  "Экшены для ПК + длинные сессии = Battlefield"
  (declare (salience 10))
  (stage inference)
  (action-pc да)
  (user-input (short-sessions нет))
  (not (final-result ?))
  =>
  (assert (final-result Battlefield))
  (printout t "[Правило 19] Экшены для ПК + длинные сессии => Battlefield" crlf))

;; Экшены для консолей
(defrule rule-20-action-console-short
  "Экшены для консолей + короткие сессии = Halo"
  (declare (salience 10))
  (stage inference)
  (action-console да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Halo))
  (printout t "[Правило 20] Экшены для консолей + короткие сессий => Halo" crlf))

(defrule rule-21-action-console-long
  "Экшены для консолей + длинные сессии = God of War"
  (declare (salience 10))
  (stage inference)
  (action-console да)
  (user-input (short-sessions нет))
  (not (final-result ?))
  =>
  (assert (final-result God-of-War))
  (printout t "[Правило 21] Экшены для консолей + длинные сессии => God of War" crlf))

;; RPG для ПК
(defrule rule-22-rpg-pc-short
  "RPG для ПК + короткие сессии = The Witcher"
  (declare (salience 10))
  (stage inference)
  (rpg-pc да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result The-Witcher))
  (printout t "[Правило 22] RPG для ПК + короткие сессии => The Witcher" crlf))

(defrule rule-23-rpg-pc-long
  "RPG для ПК + длинные сессии = Skyrim"
  (declare (salience 10))
  (stage inference)
  (rpg-pc да)
  (user-input (short-sessions нет))
  (not (final-result ?))
  =>
  (assert (final-result Skyrim))
  (printout t "[Правило 23] RPG для ПК + длинные сессии => Skyrim" crlf))

;; RPG для консолей
(defrule rule-24-rpg-console-short
  "RPG для консолей + короткие сессии = Final Fantasy"
  (declare (salience 10))
  (stage inference)
  (rpg-console да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Final-Fantasy))
  (printout t "[Правило 24] RPG для консолей + короткие сессии => Final Fantasy" crlf))

;; Стратегии для ПК
(defrule rule-25-strategy-pc-short
  "Стратегии для ПК + короткие сессии = Age of Empires"
  (declare (salience 10))
  (stage inference)
  (strategy-pc да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Age-of-Empires))
  (printout t "[Правило 25] Стратегии для ПК + короткие сессии => Age of Empires" crlf))

(defrule rule-26-strategy-pc-long
  "Стратегии для ПК + длинные сессии = Civilization"
  (declare (salience 10))
  (stage inference)
  (strategy-pc да)
  (user-input (short-sessions нет))
  (not (final-result ?))
  =>
  (assert (final-result Civilization))
  (printout t "[Правило 26] Стратегии для ПК + длинные сессии => Civilization" crlf))

;; Стратегии для консолей
(defrule rule-27-strategy-console-short
  "Стратегии для консолей + короткие сессии = XCOM"
  (declare (salience 10))
  (stage inference)
  (strategy-console да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result XCOM))
  (printout t "[Правило 27] Стратегии для консолей + короткие сессии => XCOM" crlf))

;; Приключения для ПК
(defrule rule-28-adventure-pc-short
  "Приключения для ПК + короткие сессии = Batman: Arkham"
  (declare (salience 10))
  (stage inference)
  (adventure-pc да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Batman-Arkham))
  (printout t "[Правило 28] Приключения для ПК + короткие сессии => Batman: Arkham" crlf))

;; Приключения для консолей
(defrule rule-29-adventure-console-short
  "Приключения для консолей + короткие сессии = Uncharted"
  (declare (salience 10))
  (stage inference)
  (adventure-console да)
  (user-input (short-sessions да))
  (not (final-result ?))
  =>
  (assert (final-result Uncharted))
  (printout t "[Правило 29] Приключения для консолей + короткие сессии => Uncharted" crlf))

(defrule rule-30-adventure-console-long
  "Приключения для консолей + длинные сессии = The Legend of Zelda"
  (declare (salience 10))
  (stage inference)
  (adventure-console да)
  (user-input (short-sessions нет))
  (not (final-result ?))
  =>
  (assert (final-result The-Legend-of-Zelda))
  (printout t "[Правило 30] Приключения для консолей + длинные сессии => The Legend of Zelda" crlf))

;; ============================================================================
;; РАЗДЕЛ 9: ПРАВИЛА ДЛЯ СЛУЧАЯ ОТСУТСТВИЯ ПЛАТФОРМЫ
;; ============================================================================

(defrule rule-no-platform
  "Если нет доступных платформ"
  (declare (salience 10))
  (stage inference)
  (no-platform да)
  (not (final-result ?))
  =>
  (assert (final-result Нет-рекомендации))
  (printout t "[Правило No-Platform] Нет доступных платформ" crlf))

;; ============================================================================
;; РАЗДЕЛ 10: ПРАВИЛА ВЫВОДА ИТОГОВОГО РЕЗУЛЬТАТА
;; ============================================================================

(defrule display-final-recommendation-game
  "Выводит итоговую рекомендацию пользователю"
  (declare (salience 5))
  (stage inference)
  (final-result ?game)
  (not (result-displayed))
  =>
  (assert (result-displayed))
  (printout t crlf)
  (printout t "========================================" crlf)
  (printout t "  ИТОГОВАЯ РЕКОМЕНДАЦИЯ" crlf)
  (printout t "========================================" crlf)
  
  (if (eq ?game Нет-рекомендации)
    then
    (printout t "  Мы не можем подобрать игру исходя из ваших ответов." crlf)
    else
    (printout t "  Рекомендуемая игра: " ?game crlf))
  
  (printout t "========================================" crlf)
  (printout t crlf))

;; ============================================================================
;; РАЗДЕЛ 11: ПРАВИЛА ЗАВЕРШЕНИЯ РАБОТЫ
;; ============================================================================

(defrule finalize-system
  "Завершает работу экспертной системы"
  (declare (salience 1))
  (stage inference)
  (result-displayed)
  =>
  (printout t "Работа экспертной системы завершена." crlf)
  (printout t "Для просмотра всех фактов введите: (facts)" crlf)
  (printout t crlf))

;; ============================================================================
;; КОНЕЦ СКРИПТА
;; ============================================================================