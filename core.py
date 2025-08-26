import os
import requests
import bs4
from sqlalchemy import Column, Integer, String, create_engine, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def get_def_ex(word):
    url = f'https://dictionary.cambridge.org/dictionary/english/{word}'

    headers = {
        'User-Agent': 'Mozilla/4.0',
        'Accept-Language': 'en-US,en;q=0.8',
    }

    cookies = {
        'CONSENT': 'YES+',
    }

    res = requests.get(url, headers=headers, cookies=cookies)
    bs = bs4.BeautifulSoup(res.text, 'html.parser')
    defs = bs.find_all(class_ = 'def ddef_d db')
    definition = defs[0].text if len(defs) else ''
    exs = bs.find_all(class_ = 'examp dexamp')
    example1 = exs[0].text if len(exs) else ''
    example2 = exs[1].text if len(exs)>1 else ''
    return definition.strip()[:-1],example1.strip(),example2.strip()

Base = declarative_base()

class WordEntry(Base):
    __tablename__ = "words"
    id = Column(Integer, primary_key=True, autoincrement=True)
    word = Column(String, unique=True, nullable=False)
    definition = Column(String)
    example1 = Column(String)
    example2 = Column(String)
    cycle = Column(Integer, default=0)
    last_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_read = Column(DateTime(timezone=True), server_default=func.now())

# SQLite setup
SETUP_URL = (
    "postgresql://postgres.vqlgotsgopxyyftmthjr:0025422537Mm%40@"
    "aws-1-eu-north-1.pooler.supabase.com:6543/postgres?sslmode=require"
)
engine = create_engine(SETUP_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
