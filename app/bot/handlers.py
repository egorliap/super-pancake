import io

from aiohttp import ClientSession
from aiogram.types import Message, BufferedInputFile
from aiogram import Router
import pandas as pd

from app.parser.service import OzonParser


router = Router()


@router.message()
async def fetch(message:Message):
    async with ClientSession() as session:
        try:
            print(message.text)
            
            sellers = await OzonParser.get_sellers_from_category(session, message.text)
        except Exception as e:
            await message.answer(f"Error occured: {e}")
            return
    await message.answer_document(BufferedInputFile(streaming_response(sellers), "sellers_from_category.xlsx"))
    

def streaming_response(sequence: list[dict]):
    df = pd.DataFrame(sequence)
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine="xlsxwriter")
    df.to_excel(writer, index=False)
    writer.close()
    return output.getvalue()
