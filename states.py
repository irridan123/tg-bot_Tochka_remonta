from aiogram.fsm.state import State, StatesGroup

class ShiftStates(StatesGroup):
    choose_branch = State()
    choose_deal = State()
    confirm_pickup = State()
    update_model = State()
    enter_complectation = State()
    upload_files = State()
    complete_order = State()
    confirm_delivery = State()
    enter_amount = State()
    enter_reject_comment = State()
    enter_name = State()
    choose_date_change = State()  # Новое состояние для выбора изменения даты
    enter_date = State()  # Новое состояние для ввода даты