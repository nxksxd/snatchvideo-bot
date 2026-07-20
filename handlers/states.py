from aiogram.fsm.state import State, StatesGroup


class DownloadStates(StatesGroup):
    waiting_link = State()
    waiting_quality = State()
