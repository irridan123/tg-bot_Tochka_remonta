from aiogram.fsm.state import State, StatesGroup

class ShiftStates(StatesGroup):
    confirm_pickup = State()      # Подтверждение для Ветки 1
    update_model = State()        # Ввод модели для Ветки 1

    confirm_delivery = State()    # Подтверждение для Ветки 2
    enter_amount = State()        # Ввод суммы для Ветки 2