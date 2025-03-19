import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from bs4 import BeautifulSoup

from key import TOKENN

# Ваши данные для Telegram-бота
TOKEN = TOKENN

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def load_urls(filename):
    """Загрузка URL-адресов из файла."""
    with open(filename, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]  # Чтение строк и удаление пустых
    return urls


# Загрузка URL-адресов из файла
urls = load_urls('urls.txt')


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    keyboard = [
        [
            InlineKeyboardButton("Получить данные", callback_data='get_data'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Нажмите кнопку, чтобы получить данные',
                                   reply_markup=reply_markup)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки"""
    query = update.callback_query
    await query.answer()

    if query.data == 'get_data':
        messages = []

        for url in urls:
            product_data = get_product_data(url)

            if product_data:
                message = f"Название: {product_data['name']}\nЦена: {product_data['price']}\nВ наличии: {product_data['availability']}"
                messages.append(message)
            else:
                messages.append(f"Не удалось получить данные о товаре с URL: {url}")

        # Отправляем все сообщения
        await context.bot.send_message(chat_id=update.effective_chat.id, text="\n\n".join(messages))


def get_product_data(url):
    """
    Извлекает название, цену и количество товара со страницы товара.

    Args:
        url (str): URL страницы товара.

    Returns:
        dict: Словарь с названием, ценой и количеством товара.
              Возвращает None, если не удается получить данные.
    """
    try:
        # Отправляем GET-запрос на URL
        response = requests.get(url)
        response.raise_for_status()  # Проверяем на наличие ошибок при запросе

        # Создаем объект BeautifulSoup для анализа HTML
        soup = BeautifulSoup(response.content, 'html.parser')

        # Извлекаем название товара
        name_element = soup.find('div', class_='title-block__title').find('h1')
        name = name_element.text.strip() if name_element else "Название не указано"

        # Извлекаем цену товара
        price_element = soup.find('div', class_='price')
        price = price_element.text.strip() if price_element else "Цена не указана"

        # Инициализируем переменную availability
        availability = "Не указано"

        # Извлекаем информацию о наличии товара
        store_item_el = soup.find('div', class_='product-inner__item')
        if store_item_el:
            store_item_element = store_item_el.find('div', class_='product-inner__name')
            text_element = store_item_el.find('div', class_='product-inner__text')
            if text_element:
                availability_text = text_element.text.strip().lower()
                # Проверяем наличие товара
                if "есть" in availability_text:
                    availability = "В наличии"
                elif "нет" in availability_text:
                    availability = "Нет в наличии"
                else:
                    availability = "Статус наличия не определен"

        # Возвращаем данные в виде словаря
        return {
            'name': name,
            'price': price,
            'availability': availability
        }

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе страницы: {e}")
        return None
    except AttributeError as e:
        logging.error(f"Ошибка при анализе HTML: {e}")
        return None


def main():
    # Создаем экземпляр Application и передаем ему токен бота
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_click))
    asyncio.run(application.run_polling())  # Запускаем цикл событий


if __name__ == '__main__':
    main()  # Запускаем основную функцию