import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime  # Импортируем datetime для работы с датой
from key import TOKENN

TOKEN = TOKENN

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def load_urls(filename):
    """Загрузка URL-адресов из файла."""
    with open(filename, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]  # Чтение строк и удаление пустых
    return urls


# Загрузка URL-адресов из файлов
urls1 = load_urls('urls.txt')
urls2 = load_urls('urls2.txt')
urls3 = load_urls('urls3.txt')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    keyboard = [
        [
            InlineKeyboardButton("Strikeplanet", callback_data='get_data1'),
            InlineKeyboardButton("Apostol", callback_data='get_data2'),
            InlineKeyboardButton("Airsoft-rus", callback_data='get_data3'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text='Выберите источник данных:',
                                   reply_markup=reply_markup)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки"""
    query = update.callback_query
    await query.answer()

    data_to_save = []

    # Словарь для сопоставления кнопки и источника данных
    source_map = {
        'get_data1': (urls1, "strikeplanet"),
        'get_data2': (urls2, "apostol"),
        'get_data3': (urls3, "airsoft-rus"),
    }

    urls, parser = source_map.get(query.data, ([], "unknown"))

    if not urls:
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text="Неизвестный источник данных.")
        return

    for url in urls:
        product_data = get_product_data_generic(url, parser)

        if product_data:
            # Добавляем URL к данным о продукте
            product_data['url'] = url  # Добавляем новый столбец с URL
            data_to_save.append(product_data)
        else:
            logging.error(f"Не удалось получить данные о товаре с URL: {url}")

    if data_to_save:  # Проверка на пустой список
        df = pd.DataFrame(data_to_save)

        # Получаем текущую дату
        current_date = datetime.now().strftime('%Y-%m-%d')  # Формат "ГГГГ-ММ-ДД"

        # Создаем имя файла с датой
        excel_filename = f'{parser}_{current_date}.xlsx'  # Используем parser для имени файла

        df.to_excel(excel_filename, index=False)

        # Отправка файла пользователю
        with open(excel_filename, 'rb') as document:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=document)

        logging.info(f"Данные успешно сохранены и отправлены в файл {excel_filename}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Нет данных для сохранения.")


def get_product_data_generic(url, parser):
    """Извлекает данные с помощью указанного парсера."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 403:
            logging.error(f"403 Forbidden: Доступ запрещён для URL: {url}")
            return None

        response.raise_for_status()  # Проверяем на наличие ошибок при запросе
        soup = BeautifulSoup(response.content, 'html.parser')

        if parser == "strikeplanet":
            return extract_strikeplanet_data(soup)
        elif parser == "apostol":
            return extract_apostol_data(soup)
        elif parser == "airsoft-rus":
            return extract_airsoft_rus_data(soup)

        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе страницы: {e}")
        return None
    except AttributeError as e:
        logging.error(f"Ошибка при анализе HTML: {e}")
        return None


def extract_strikeplanet_data(soup):
    """Извлекает данные из страницы strikeplanet."""
    sait = "Strikeplanet"
    name_element = soup.find('div', class_='title-block__title')
    name = name_element.find('h1').text.strip() if name_element and name_element.find('h1') else "Название не указано"

    price_element = soup.find('div', class_='price')
    price = price_element.text.strip() if price_element else "Цена не указана"

    availability = "Не указано"
    store_item_e = soup.find('div', class_='product-inner__list')
    if store_item_e:
        store_item_el = store_item_e.find('div', class_='product-inner__item')
        if store_item_el:
            text_element = store_item_el.find('div', class_='product-inner__text')
            if text_element:
                availability_text = text_element.text.strip().lower()
                availability = ("В наличии" if "есть" in availability_text
                                else "Нет в наличии" if "нет" in availability_text
                else "Статус наличия не определен")

    return {'sait': sait, 'name': name, 'price': price, 'availability': availability}


def extract_apostol_data(soup):
    """Извлекает данные из страницы apostol."""
    sait = "Apostol"
    name_element = soup.find('div', class_='t-store__prod-popup__title-wrapper')
    name = name_element.find('h1',
                             class_='js-store-prod-name js-product-name t-store__prod-popup__name t-name t-name_xl').text.strip() if name_element and name_element.find(
        'h1') else "Название не указано"

    price_element = soup.find('div', class_='js-product-price js-store-prod-price-val t-store__prod-popup__price-value')
    price = price_element.text.strip() if price_element else "Цена не указана"

    availability = "Не указано"
    store_item_e = soup.find('div', class_='product-inner__list')
    if store_item_e:
        store_item_el = store_item_e.find('div', class_='product-inner__item')
        if store_item_el:
            text_element = store_item_el.find('div', class_='product-inner__text')
            if text_element:
                availability_text = text_element.text.strip().lower()
                availability = ("В наличии" if "есть" in availability_text
                                else "Нет в наличии" if "нет" in availability_text
                else "Статус наличия не определен")

    return {'sait': sait, 'name': name, 'price': price, 'availability': availability}


def extract_airsoft_rus_data(soup):
    """Извлекает данные из страницы airsoft-rus."""
    sait = "Airsoft-rus"
    name_element = soup.find('div', id='content')
    name = name_element.find('h1').text.strip() if name_element and name_element.find('h1') else "Название не указано"

    price_element = soup.find('mark', class_='price')
    price = price_element.text.strip() if price_element else "Цена не указана"

    store_item_e = soup.find('p', class_='in_stock')
    availability = store_item_e.text.strip() if store_item_e else "Нет в наличии"

    return {'sait': sait, 'name': name, 'price': price, 'availability': availability}


def main():
    """Главная функция для запуска бота."""
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))

    asyncio.run(application.run_polling())  # Запускаем цикл событий


if __name__ == '__main__':
    main()  # Запускаем основную функцию


