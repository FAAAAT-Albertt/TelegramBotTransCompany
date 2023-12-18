"""code payment"""
from aiogram import Bot, Dispatcher, F, types
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import (FSInputFile, InlineKeyboardButton,
                           InlineKeyboardMarkup, KeyboardButton, Message,
                           ReplyKeyboardRemove, LabeledPrice)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.utils.markdown import hbold, hitalic, hlink
from aiogram.methods.send_invoice import SendInvoice

from typing import *
import config

async def command_buy_handler(message: Message, bot: Bot, summ: float) -> NoReturn:
    """payment for users"""
    await bot(SendInvoice(
        chat_id=message.chat.id,
        title="____TEST____",
        description="test payment",
        payload="payment through a bot",
        provider_token=config.PAYMENT_TOKEN,
        currency="rub",
        prices=[
            LabeledPrice(
                label="Оплата услуг",
                amount=summ*100
            )
        ],
    ))
