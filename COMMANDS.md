### Реализованные команды:

1.  **/start**
    -   **Описание**: Регистрирует пользователя, если он не зарегистрирован, и отправляет приветственное сообщение.
    -   **Пример запуска**
        ```
        /start
        ```
        
2. **/set_admin**

   -   **Описание**: Назначает нового администратора. Доступно только действующим администраторам. 
   -   **Пример запуска**:
        ```
       /set_admin 123456789
       ```
   -   Здесь `123456789` представляет собой Telegram ID нового администратора.

3.  **/create_poll**
    -   **Описание**: Создаёт опрос для тренировки. Доступно только администраторам.
    -   **Пример запуска**:
        
        ```
        /create_poll 2024-11-20 18:00 Центр 1000
        ```
        
    -   Параметры: дата тренировки, время, место проведения и стоимость участия.
4. **/pay** 
    - **Описание**: Регистрирует произведённую оплату пользователем.
    - **Пример запуска**:
        ```
        /pay 500 
        ``` 
   -   Где `500` — это сумма, которую пользователь хочет внести.

5. **/balance**
   - **Описание**: Отправляет пользователю его текущий баланс.
   - **Пример запуска**:
      ```
     /balance
        ```      

6.  **/all_balances**
    -   **Описание**: Администратор получает отчёт о балансе всех участников.
    -   **Пример запуска**:        
        ```
        /all_balances
        ```        

7.  **/set_initial_balance** 
    -   **Описание**: Устанавливает начальный баланс для пользователя. Доступно только администраторам.
    -   **Пример запуска**:     
        ```
        /set_initial_balance 123456789 1000
        ```
    -   Где `123456789` — это Telegram ID пользователя, а `1000` — сумма начального баланса.

### Примечания
-   **Администраторские права**: Некоторые команды, такие как `/set_admin`, `/create_poll`, `/all_balances`, и `/set_initial_balance`, требуют наличия администраторских прав.
-   **Формат ввода**: Убедитесь, что команды вводятся в правильном формате с необходимыми параметрами (например, ID пользователя, сумма и т.д.), чтобы бот смог их корректно обработать.
