from flask import Flask, request, jsonify
import telebot
from telebot import types
import sqlite3
import random
import string

app = Flask(__name__)

TELEGRAM_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'
bot = telebot.TeleBot(token=TELEGRAM_TOKEN)


# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            chat_id INTEGER PRIMARY KEY,
            phone_number TEXT,
            discount_code TEXT
        )
    ''')
    conn.commit()
    conn.close()


init_db()


# Генерация случайного кода скидки
def generate_discount_code(length=6):
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


@app.route('/apply_discount', methods=['POST'])
def apply_discount():
    data = request.get_json()
    phone_number = data.get('phone_number')
    discount_code = data.get('discount_code')

    if not phone_number or not discount_code:
        return jsonify({'status': 'error', 'message': 'Phone number or discount code not provided'}), 400

    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('SELECT chat_id FROM users WHERE phone_number = ?', (phone_number,))
    result = cursor.fetchone()

    if result:
        chat_id = result[0]
        # Сохранение кода скидки в базе данных
        cursor.execute('UPDATE users SET discount_code = ? WHERE phone_number = ?', (discount_code, phone_number))
        conn.commit()
        conn.close()

        try:
            bot.send_message(chat_id,
                             f"Ваш код скидки: {discount_code}. Пожалуйста, сообщите его кассиру для получения скидки.")
            return jsonify({'status': 'ok', 'message': 'Discount code sent successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    else:
        conn.close()
        return jsonify({'status': 'error', 'message': 'Phone number not found'}), 404


@app.route('/send_invoice', methods=['POST'])
def send_invoice():
    data = request.get_json()
    invoice_number = data.get('invoice_number')
    invoice_date = data.get('invoice_date')
    invoice_amount = data.get('invoice_amount')

    if not invoice_number or not invoice_date or not invoice_amount:
        return jsonify({'status': 'error', 'message': 'Incomplete invoice data'}), 400

    chat_id = 'YOUR_CHAT_ID'  # Замените на ваш chat_id или возьмите из базы данных

    message = f"Фактура завершена:\nНомер: {invoice_number}\nДата: {invoice_date}\nСумма: {invoice_amount}"

    try:
        bot.send_message(chat_id, message)
        return jsonify({'status': 'ok', 'message': 'Invoice sent successfully'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data(as_text=True)
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return jsonify({'status': 'ok'})


@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = message.chat.id
    # Кнопка для отправки номера телефона
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button = types.KeyboardButton('Предоставить контакт', request_contact=True)
    markup.add(button)
    bot.send_message(chat_id, 'Здравствуйте! Пожалуйста, отправьте мне свой номер телефона. Нужно просто нажать '
                              'кнопку отправить, которая появилась внизу.', reply_markup=markup)


@bot.message_handler(content_types=['contact'])
def handle_contact(message):
    chat_id = message.chat.id
    phone_number = message.contact.phone_number

    # Сохранение данных в базе
    conn = sqlite3.connect('users.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO users (chat_id, phone_number) VALUES (?, ?)', (chat_id, phone_number))
    conn.commit()
    conn.close()

    bot.send_message(chat_id,
                     f"Спасибо! Ваш номер телефона ({phone_number}) получен. Теперь вам будут доступны все возможности.")


if __name__ == '__main__':
    bot.polling(none_stop=True)
    app.run(host='0.0.0.0', port=5020)

