import os
from supabase import create_client
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

# ============================================
# ТВОИ КЛЮЧИ
# ============================================
SUPABASE_URL = 'https://bgdtfhwqqzgggpicuyjp.supabase.co'
SUPABASE_SERVICE_KEY = 'sb_service_role_afN1H7P0K8vX3mQ9wR2tY6uI5oL4dJ3bB2nM1kL0p'
BOT_TOKEN = '8692545625:AAEcjNzfFrz1jlLs-i5jjoebqa2XauCurhI'  # ← ЗАМЕНИ на токен от @BotFather
ADMIN_USERNAME = 'SmitNeoHelp'  # ← ЗАМЕНИ на свой username без @

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

async def start(update: Update, context):
    user = update.effective_user
    username = user.username or "unknown"
    allowed = supabase.table('allowed_shops').select('*').eq('username', username).execute()
    
    if allowed.data:
        active_news = supabase.table('news').select('*').eq('shop_name', username).eq('status', 'published').execute()
        
        if active_news.data:
            keyboard = [[InlineKeyboardButton("🗑️ Удалить мою новость", callback_data='delete_my_news')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                'ℹ️ У вас уже есть опубликованная новость. Сначала удалите её.',
                reply_markup=reply_markup
            )
        else:
            keyboard = [[InlineKeyboardButton("📢 Выложить новость", callback_data='publish_news')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                '👋 Добро пожаловать! У вас есть доступ к публикации новостей.\n'
                'Нажмите кнопку, чтобы написать новость.',
                reply_markup=reply_markup
            )
    else:
        await update.message.reply_text('⛔ У вас нет доступа к публикации новостей.')

async def button_handler(update: Update, context):
    query = update.callback_query
    await query.answer()
    user = query.from_user
    username = user.username or "unknown"
    
    if query.data == 'publish_news':
        context.user_data['awaiting_news'] = True
        await query.message.reply_text('📝 Напишите текст новости в одном сообщении.')
    
    elif query.data == 'delete_my_news':
        supabase.table('news').delete().eq('shop_name', username).eq('status', 'published').execute()
        await query.message.reply_text('🗑️ Ваша новость удалена. Можете опубликовать новую.')
        keyboard = [[InlineKeyboardButton("📢 Выложить новость", callback_data='publish_news')]]
        await query.message.reply_text('Нажмите, чтобы написать:', reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context):
    user = update.effective_user
    username = user.username or "unknown"
    text = update.message.text
    
    if context.user_data.get('awaiting_news'):
        allowed = supabase.table('allowed_shops').select('*').eq('username', username).execute()
        if not allowed.data:
            await update.message.reply_text('⛔ У вас нет доступа.')
            return
        
        supabase.table('news').insert({
            'shop_name': username,
            'message': text,
            'status': 'published',
            'created_at': 'now()'
        }).execute()
        
        context.user_data['awaiting_news'] = False
        
        keyboard = [[InlineKeyboardButton("🗑️ Удалить мою новость", callback_data='delete_my_news')]]
        await update.message.reply_text('✅ Новость опубликована!', reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        allowed = supabase.table('allowed_shops').select('*').eq('username', username).execute()
        if allowed.data:
            active = supabase.table('news').select('*').eq('shop_name', username).eq('status', 'published').execute()
            if active.data:
                keyboard = [[InlineKeyboardButton("🗑️ Удалить мою новость", callback_data='delete_my_news')]]
                await update.message.reply_text('ℹ️ У вас уже есть новость.', reply_markup=InlineKeyboardMarkup(keyboard))
            else:
                keyboard = [[InlineKeyboardButton("📢 Выложить новость", callback_data='publish_news')]]
                await update.message.reply_text('Нажмите, чтобы написать новость:', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await update.message.reply_text('⛔ У вас нет доступа.')

async def add_shop(update: Update, context):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text('⛔ Только создатель может добавлять магазины.')
        return
    try:
        target_username = context.args[0]
        shop_name = ' '.join(context.args[1:]) if len(context.args) > 1 else target_username
        supabase.table('allowed_shops').upsert({'username': target_username, 'shop_name': shop_name}).execute()
        await update.message.reply_text(f'✅ @{target_username} добавлен в Белый Список!')
    except:
        await update.message.reply_text('/addshop username Название')

async def remove_shop(update: Update, context):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text('⛔ Только создатель может удалять.')
        return
    try:
        target = context.args[0]
        supabase.table('allowed_shops').delete().eq('username', target).execute()
        await update.message.reply_text(f'🗑️ @{target} удалён.')
    except:
        await update.message.reply_text('/removeshop username')

async def list_shops(update: Update, context):
    if update.effective_user.username != ADMIN_USERNAME:
        await update.message.reply_text('⛔ Только создатель.')
        return
    shops = supabase.table('allowed_shops').select('*').execute()
    if shops.data:
        msg = '✅ Белый Список:\n' + '\n'.join([f'- @{s["username"]} ({s["shop_name"]})' for s in shops.data])
    else:
        msg = 'Список пуст.'
    await update.message.reply_text(msg)

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('addshop', add_shop))
    app.add_handler(CommandHandler('removeshop', remove_shop))
    app.add_handler(CommandHandler('listshops', list_shops))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == '__main__':
    main()
