import asyncio
from pprint import pprint

import httpx
from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import Message
from environs import Env

dp = Dispatcher()


async def poll_devman_api(bot: Bot, chat_id: int, api_key: str):
    url = "https://dvmn.org/api/long_polling/"
    headers = {"Authorization": f"Token {api_key}"}
    params = {"timestamp": None}

    async with httpx.AsyncClient() as client:
        while True:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=90)
                data = response.json()

                if data.get("status") == "found":
                    pprint(data)
                    await send_notification(bot, chat_id, data)
                    params["timestamp"] = data.get("last_attempt_timestamp")

                elif data.get("status") == "timeout":
                    print("Новых данных нет")
                    params["timestamp"] = data.get("timestamp_to_request")

            except httpx.ConnectError:
                print("Проблемы с соединением. Повторная попытка через 5 секунд...")
                await asyncio.sleep(5)
            except httpx.ReadTimeout:
                print("Сервер не отвечает. Повторный запрос через 5 секунд...")
                await asyncio.sleep(5)


async def send_notification(bot: Bot, chat_id: int, data: dict):
    new_attempts = data.get("new_attempts")
    if not new_attempts:
        await bot.send_message(chat_id, text="Обнаружена проверка, но деталей нет :(")
        return
    attempt = new_attempts[0]

    text = (
        f"Твою работу проверили!\n"
        f"Получено код-ревью по уроку: {attempt.get('lesson_title')}\n"
        f"Статус работы: {'нуждается в доработке' if attempt.get('is_negative') else 'принята'}\n"
        f"Можно посмотреть по ссылке: {attempt.get('lesson_url')}"
    )
    await bot.send_message(chat_id, text=text)


@dp.message(CommandStart())
async def command_start_handler(message: Message, allowed_chat_id: int):
    chat_id = message.chat.id
    if chat_id != allowed_chat_id:
        await message.answer("Прости, но я проверяю только Катины домашние работы!")
    else:
        await message.answer("Привет, Катя! Начинаю следить за твоими работами!")


@dp.message()
async def text_message_handler(message: Message, allowed_chat_id: int):
    chat_id = message.chat.id
    if chat_id != allowed_chat_id:
        await message.answer("Прости, но я проверяю только Катины домашние работы!")
    else:
        await message.answer(
            "Я слишком туп, чтобы что-то отвечать, но я жив и все еще слежу за твоими работами!"
        )


async def main():
    env = Env()
    env.read_env()
    tg_token = env.str("TG_TOKEN")
    allowed_chat_id = env.int("ALLOWED_CHAT_ID")
    api_key = env.str("API_KEY")

    bot = Bot(token=tg_token)

    asyncio.create_task(poll_devman_api(bot, allowed_chat_id, api_key))
    await dp.start_polling(bot, allowed_chat_id=allowed_chat_id)


if __name__ == "__main__":
    asyncio.run(main())
