АВТОРИЗАЦИЯ КУРЬЕРОВ:
1. Откройте файл user_data.json в корне проекта.
2. Добавьте в него информацию о пользователях в формате:
{
    "tg_id": { 
        "bitrix_id": bitrix_id,
        "name": ""
    },
    ...
}
3. Сохраните файл.

tg_id: Получить Tg ID: Можно написать боту в Телеграм @userinfobot и он покажет ваш ID. ссылка - https://t.me/userinfobot
bitrix_id: Получить bitrix_id: Можно в профиле Битрикс24, в URL будет что-то вроде /company/personal/user/755/, где 755 - это bitrix_id
name: name - это имя, которое будет отображаться в боте, его оставляем пустым.

таким образом, файл user_data.json должен выглядеть примерно так:
{
    "1389473957": { 
        "bitrix_id": 755,
        "name": "\u041d\u0443\u0440\u0441\u0443\u043b\u0442\u0430\u043d"
    },
    "1234567890": { 
        "bitrix_id": 123,
        "name": "\u041d\u0443\u0440\u0441\u0443\u043b\u0442\u0430\u043d"
    }
}

ЗАПУСК СЕРВЕРА:
1. Запустите start_server.bat в корне папки
2. Ждите данного сообщения - INFO:aiogram.dispatcher:Run polling for bot @tochka_remonta_delivery_bot id=7954191958 - 'tochka_remonta'
3. Поздравляю, вы запустили сервер! Ваш тг бот работает. 