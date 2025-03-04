from telebot import TeleBot, types
from collections import Counter
import requests
import vk_api
import os
from config import QUESTIONS, ANIMAL_IMAGES

# Initialize the bot
bot = TeleBot('7033169281:AAGLJ09I_XPJY-1eCQV4CAvuWfjg681JYQ8')

# Utility function to create a reply keyboard markup
def create_markup(buttons):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for button in buttons:
        markup.add(types.KeyboardButton(button))
    return markup

# User class to manage user state
class User:
    def __init__(self):
        self.question_index = 0
        self.answers = []
        self.state = None  # Add a state attribute

# User states and answers
user_states = {}
user_answers = {}

# Command handler for /start
@bot.message_handler(commands=['start'])
def start(message):
    buttons = ["👋 Поздороваться"]
    markup = create_markup(buttons)
    bot.send_message(message.from_user.id, "👋 Приветствуем Вас в нашем боте!!", reply_markup=markup)

# Text message handler
@bot.message_handler(content_types=['text'])
def get_text_messages(message):
    user_id = message.from_user.id

    if message.text == '👋 Поздороваться':
        buttons = ['⚜ Узнать свое тотемное животное', '💚 Официальный сайт Московского зоопарка', '💲 Наша спонсорская программа']
        markup = create_markup(buttons)
        bot.send_message(user_id, '❓ Задайте интересующий вас вопрос', reply_markup=markup)

    elif message.text == '⚜ Узнать свое тотемное животное':
        user_states[user_id] = User()  # Start the quiz
        user_states[user_id].state = "quiz"  # Set the state to "quiz"
        user_answers[user_id] = []  # Initialize the user's answers
        send_question(user_id)

    elif user_id in user_states:
        process_answer(user_id, message.text)

    elif message.text == '💚 Официальный сайт Московского зоопарка':
        bot.send_message(user_id, 'Перейти на сайт [ссылке](https://moscowzoo.ru/)', parse_mode='Markdown')

    elif message.text == '💲 Наша спонсорская программа':
        bot.send_message(user_id, 'Узнать подробнее на официальном сайте [ссылке](https://moscowzoo.ru/about/guardianship/waiting-guardianship/)', parse_mode='Markdown')

# Function to send a quiz question
def send_question(user_id):
    if user_id not in user_states:
        user_states[user_id] = User()

    user = user_states[user_id]
    question_data = QUESTIONS[user.question_index]
    question_text = question_data['question']
    answers = question_data['answers']

    buttons = list(answers.keys())  # Get the list of answer options
    markup = create_markup(buttons)
    bot.send_message(user_id, question_text, reply_markup=markup)

# Function to process user answers
def process_answer(user_id, answer):
    user = user_states.get(user_id)  # Ensure this gets the User object.

    # Check if user is not None and is an instance of User
    if user and isinstance(user, User):
        if user.state == "quiz":  # Only process answers if the user is in the quiz state
            question_index = user.question_index
            if 0 <= question_index < len(QUESTIONS):
                correct_answers = QUESTIONS[question_index]['answers']

                if answer in correct_answers:
                    user.answers.extend(correct_answers[answer])  # Store the correct answers
                    user_answers[user_id].extend(correct_answers[answer])  # Update user_answers
                    bot.send_message(user_id, "Ответ принят!")
                else:
                    bot.send_message(user_id, "Неправильный ответ. Пожалуйста, выберите один из предложенных вариантов.")

                # Move to the next question or finish the quiz
                if question_index < len(QUESTIONS) - 1:
                    user.question_index += 1
                    send_question(user_id)
                else:
                    calculate_results(user_id)
            else:
                bot.send_message(user_id, "Произошла ошибка. Попробуйте снова.")
        else:
            # If the user is not in the quiz state, ignore the message
            pass
    else:
        bot.send_message(user_id, "User not found. Please start over.")
        return  # Exit the function if user is invalid

# Function to calculate quiz results
def calculate_results(user_id):
    animal_counts = Counter(user_answers[user_id])

    if not animal_counts:  # Check if there are no answers
        bot.send_message(user_id, "Вы не ответили на вопросы. Пожалуйста, пройдите викторину снова.")
        return

    max_count = max(animal_counts.values())
    top_animals = [animal for animal, count in animal_counts.items() if count == max_count]

    result_message = "Ваши тотемные животные (с наибольшим количеством голосов): \n"
    for animal in top_animals:
        result_message += f"{animal}: {max_count} раз(а)\n"
        if animal in ANIMAL_IMAGES:
            try:
                # Fetch the image with a timeout
                response = requests.get(ANIMAL_IMAGES[animal], timeout=10)
                response.raise_for_status()  # Check for HTTP errors
                bot.send_photo(user_id, response.content)
            except requests.exceptions.RequestException as e:
                print(f"Error fetching image for {animal}: {e}")
                bot.send_message(user_id, f"Не удалось загрузить изображение для {animal}. Пожалуйста, попробуйте позже.")
            except Exception as e:
                print(f"Unexpected error for {animal}: {e}")
                bot.send_message(user_id, f"Произошла ошибка при обработке изображения для {animal}.")

    bot.send_message(user_id, result_message)
    select_animal(user_id, top_animals)

# Function to select an animal
def select_animal(user_id, animals):
    buttons = animals + ["🔙 Вернуться в меню"]  # Combine animals and the back button
    markup = create_markup(buttons)
    bot.send_message(user_id, "Выберите одно из тотемных животных, чтобы стать его спонсором:", reply_markup=markup)

    # Ensure user is an instance of User
    user = user_states.get(user_id)
    if user:
        user.state = "selecting_animal"  # Set the state attribute
    else:
        user_states[user_id] = User()  # Create a new User instance if it doesn't exist
        user_states[user_id].state = "selecting_animal"

# Handler for animal selection
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id) and user_states[message.from_user.id].state == "selecting_animal")
def handle_animal_selection(message):
    user_id = message.from_user.id
    selected_animal = message.text

    if selected_animal == "🔙 Вернуться в меню":
        # Return to the main menu
        start(message)
        return

    if selected_animal not in ANIMAL_IMAGES:
        bot.send_message(user_id, "Выберите корректное животное из списка.")
        return

    # Handle the selected animal
    animal_chosen(user_id, selected_animal)
    print("Handling animal selection")

def animal_chosen(user_id, chosen_animal):
    if chosen_animal not in ANIMAL_IMAGES:
        bot.send_message(user_id, "Вы выбрали неверное животное.")
        return

    # Send a confirmation message
    bot.send_message(user_id, f"Вы выбрали {chosen_animal}. Спасибо!")

    # Send the image of the chosen animal
    image_url = ANIMAL_IMAGES[chosen_animal]
    try:
        response = requests.get(image_url, timeout=10)
        response.raise_for_status()  # Check for HTTP errors
        bot.send_photo(user_id, response.content)
    except requests.exceptions.RequestException as e:
        print(f"Error fetching image: {e}")
        bot.send_message(user_id, f"Не удалось загрузить изображение для {chosen_animal}. Пожалуйста, попробуйте позже.")
    except Exception as e:
        print(f"Unexpected error: {e}")
        bot.send_message(user_id, f"Произошла ошибка при обработке изображения для {chosen_animal}.")

    # Post to VK (if applicable)
    post_to_vk(user_id, chosen_animal, image_url)

    # Reset the user's state
    user_states.pop(user_id, None)
    user_answers.pop(user_id, None)

    # Set a new state or reset to the initial state
    user_states[user_id] = User()
    user_states[user_id].question_index = 0
    user_states[user_id].state = 'interacting'
    print("Animal chosen")

# Function to post to VK
def post_to_vk(user_id, selected_animal, image_url):
    vk_token = 'YOUR_ACTUAL_VK_TOKEN'  # Replace with your actual VK token
    vk_session = vk_api.VkApi(token=vk_token)
    vk = vk_session.get_api()

    try:
        # Form the text of the message
        message = f"Я выбрал стать спонсором {selected_animal}!"

        # Get the URL for uploading the image
        response = vk.photos.getWallUploadServer()
        upload_url = response['upload_url']

        # Upload the image with a timeout
        try:
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()  # Check for HTTP errors
        except requests.exceptions.RequestException as e:
            bot.send_message(user_id, "Не удалось загрузить изображение. Пожалуйста, попробуйте позже.")
            print(f"Error fetching image: {e}")
            return

        # Upload the image to VK
        files = {'file': ('image.jpg', response.content)}
        upload_response = requests.post(upload_url, files=files, timeout=10)
        upload_response.raise_for_status()
        upload_response = upload_response.json()

        # Save the image on the VK wall
        save_response = vk.photos.saveWallPhoto(
            server=upload_response['server'],
            photo=upload_response['photo'],
            hash=upload_response['hash']
        )

        # Get the ID of the uploaded photo
        photo_id = save_response[0]['id']
        owner_id = save_response[0]['owner_id']

        # Post the message on the VK wall
        vk.wall.post(
            owner_id=owner_id,
            from_group=1,
            message=message,
            attachments=f'photo{owner_id}_{photo_id}'
        )

        bot.send_message(user_id, "Ваше сообщение опубликовано в ВКонтакте! Вы можете поделиться им с друзьями.")
    except vk_api.exceptions.ApiError as e:
        bot.send_message(user_id, "Произошла ошибка при работе с ВКонтакте.")
        print(f"VK API Error: {e}")
    except requests.exceptions.RequestException as e:
        bot.send_message(user_id, "Произошла ошибка при подключении к серверу. Пожалуйста, попробуйте позже.")
        print(f"Network Error: {e}")
    except Exception as e:
        bot.send_message(user_id, "Произошла непредвиденная ошибка. Пожалуйста, попробуйте позже.")
        print(f"Unexpected Error: {e}")

# Start the bot
bot.polling(none_stop=True, interval=0)