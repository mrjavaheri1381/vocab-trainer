from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from datetime import datetime
import pandas as pd
import os
import json
from dotenv import load_dotenv
from core import Session, WordEntry, get_def_ex
import telegram
from bot import setup_bot, TOKEN, bot

load_dotenv()
queue = []

app = FastAPI()
templates = Jinja2Templates(directory="templates")
application = setup_bot()

@app.on_event("shutdown")
def save_state():
    with open('./review.json','w') as f:
        json.dump(app.state.review_detail,f)


@app.post("/webhook")
async def handle_telegram_update(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, bot)
    await application.process_update(update)
    return {"status": "ok"}


@app.on_event("startup")
async def startup_event():
    webhook_url = os.getenv("WEBHOOK_URL")
    await bot.set_webhook(url=f"{webhook_url}/webhook")

    app.state.review_detail = json.loads(open('./review.json','r').read())
    app.state.queue = []
    session = Session()
    if session.query(WordEntry).first() is None:
        df = pd.read_csv("./data/words.csv")
        for _, row in df.iterrows():
            if pd.isna(row["Definition"]):
                continue
            word = row["Word"]
            if session.query(WordEntry).filter_by(word=word).first():
                continue
            session.add(WordEntry(
                word=word,
                definition=row["Definition"],
                example1=row.get("Example 1", ""),
                example2=row.get("Example 2", ""),
                cycle=0,
                last_seen=datetime.now()
            ))
        session.commit()
    session.close()


def count_words_seen_today(word_id):
    db = Session()

    today_start = datetime.combine(datetime.today(), datetime.min.time())
    today = db.query(WordEntry)\
        .filter(WordEntry.last_read >= today_start)\
        .count()
    remaining = db.query(WordEntry)\
        .filter(WordEntry.id > word_id)\
        .filter(WordEntry.cycle == 0)\
        .count()

    db.close()
    return f"Today: {today}     Remaining: {remaining}"

@app.get("/", response_class=HTMLResponse)
def show_word(request: Request):
    review = 0
    session = Session()
    if(app.state.queue):
        word_id = app.state.queue[0]
        word = session.query(WordEntry).get(word_id)
        review = 1
    else:    
        word = session.query(WordEntry).order_by(WordEntry.last_seen).first()
        word_id = word.id
        while word.cycle > 0:
            word.last_seen = datetime.now()
            word.cycle -= 1
            word = session.query(WordEntry).order_by(WordEntry.last_seen).first()
            word_id = word.id
    
    word_data = {
        "id": word.id,
        "word": word.word,
        "definition": word.definition,
        "example1": word.example1,
        "example2": word.example2,
        "review" : review
    }

    session.commit()
    session.close()

    return templates.TemplateResponse("index.html", {
        "request": request,
        "word_entry": word_data,
        "show_rating": False,
        "error": None,
        "today_count" : count_words_seen_today(word_id),
        "review":review
    })

@app.post("/", response_class=HTMLResponse)
def check_word(request: Request, user_input: str = Form(...), word_id: int = Form(...), review:int = Form(...)):
    session = Session()
    word = session.query(WordEntry).get(word_id)
    word_id = word.id

    if not word:
        session.close()
        return RedirectResponse("/")
    
    if user_input.strip().lower() == word.word.strip().lower():
        session.close()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "word_entry": word,
            "show_rating": True,
            "error": None,
            "today_count" : count_words_seen_today(word_id),
            "review":review
             
        })
    else:
        session.close()
        return templates.TemplateResponse("index.html", {
            "request": request,
            "word_entry": word,
            "show_rating": False,
            "error": "Incorrect! Try again.",
             "today_count" : count_words_seen_today(word_id),
            "review":review
        })

@app.post("/rate", response_class=HTMLResponse)
def rate_word(request: Request, rating: int = Form(...), word_id: int = Form(...), review:int = Form(...)):
    session = Session()
    if(review):
        app.state.queue.pop(0)
    else:
        app.state.review_detail['remained_word'] -= 1
        if(app.state.review_detail['remained_word'] == 0):
            app.state.review_detail['remained_word'] = int(os.getenv("REVIEW_CYCLE"))
            app.state.queue = app.state.review_detail['review_list']
            app.state.review_detail['review_list'] = []

    word = session.query(WordEntry).get(word_id)
    if word:
        word.last_seen = datetime.now()
        word.last_read = datetime.now()
        if rating == -1:
            word.cycle = 9999
        else:
            word.cycle = rating
            if(rating == 0):
                app.state.review_detail['review_list'].append(word_id)
                print(app.state.review_detail['review_list'])
                
        session.commit()
    session.close()
    return RedirectResponse("/", status_code=303)

# نمایش فرم
@app.get("/add-word", response_class=HTMLResponse)
async def add_word_form(request: Request):
    return templates.TemplateResponse("add_word.html", {"request": request, 'stat': 0})



def add_to_database(request: Request, word, definition, example1, example2):
    db = Session()
    existing = db.query(WordEntry).filter_by(word=word).first()
    if existing:
        db.close()
        return templates.TemplateResponse("add_word.html", {"request": request, 'stat': 2})


    new_entry = WordEntry(
        word=word,
        definition=definition,
        example1=example1,
        example2=example2,
        cycle=0,
        last_seen=db.query(WordEntry).order_by(WordEntry.last_seen).all()[-1].last_seen,
        last_read=datetime.now()  
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)
    db.close()

    return templates.TemplateResponse("add_word.html", {"request": request, 'stat': 1})


# دریافت فرم
@app.post("/add-word", response_class=HTMLResponse)
async def add_word(request: Request, word: str = Form(...)):
    definition, example1, example2 = get_def_ex(word)
    return add_to_database(request, word, definition, example1, example2)



@app.post("/test", response_class=JSONResponse)
async def add_word(request: Request, word=Query(...)):
    definition, example1, example2 = get_def_ex(word)
    add_to_database(request, word, definition, example1, example2)
    print(word,'Added!')
    