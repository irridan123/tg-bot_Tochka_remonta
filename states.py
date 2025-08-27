from aiogram.fsm.state import State, StatesGroup

class ShiftStates(StatesGroup):
    choose_branch = State()       # Ожидание выбора ветки
    confirm_pickup = State()      # Подтверждение для Ветки 1
    update_model = State()        # Ввод модели для Ветки 1
    complete_order = State()      # Ожидание завершения заказа (кнопка)
    enter_reject_comment = State()  # Ожидание ввода комментария при отказе

    confirm_delivery = State()    # Подтверждение для Ветки 2
    enter_amount = State()        # Ввод суммы для Ветки 2
    enter_name = State()          # Новое: Ожидание ввода имени для /set_name