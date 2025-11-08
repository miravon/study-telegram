import asyncio
import json
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from aiohttp import web

GOALS_FILE = 'user_goals.json'

def load_goals():
    try:
        with open(GOALS_FILE, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_goals(goals):
    with open(GOALS_FILE, 'w') as f:
        json.dump(goals, f, indent=4)

goals_data = load_goals()

# Webhook handlers for Render
async def health_check(request):
    return web.Response(text="Bot is running!")

async def webhook_handler(request):
    return web.Response(text="OK")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_text = """👋 Welcome to Study Reminder Bot!

I'll help you track your study goals and send you daily reminders.

📚 Available Commands:
/addgoal - Add a new study goal
/goals - View all your goals
/stats - See your progress statistics
/setreminder - Set daily reminder time
/help - Show all commands

Get started by adding your first goal with /addgoal!"""
    await update.message.reply_text(welcome_text)

async def add_goal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "📝 Usage: /addgoal <subject> <goal description>\n\n"
            "Example: /addgoal math Complete chapter 5 exercises"
        )
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Please provide both subject and goal description!")
        return
    
    user_id = str(update.effective_user.id)
    subject = context.args[0].lower()
    goal_text = ' '.join(context.args[1:])
    
    if user_id not in goals_data:
        goals_data[user_id] = {
            'goals': [],
            'reminder_time': '09:00',
            'username': update.effective_user.first_name
        }
    
    goal_entry = {
        'subject': subject,
        'goal': goal_text,
        'completed': False,
        'created': datetime.now().strftime('%Y-%m-%d')
    }
    
    goals_data[user_id]['goals'].append(goal_entry)
    save_goals(goals_data)
    
    await update.message.reply_text(
        f"✅ Goal added!\n\n"
        f"📚 Subject: *{subject.upper()}*\n"
        f"🎯 Goal: {goal_text}",
        parse_mode='Markdown'
    )

async def view_goals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in goals_data or not goals_data[user_id]['goals']:
        await update.message.reply_text(
            "You have no goals set yet! 📝\n"
            "Use /addgoal to add your first goal."
        )
        return
    
    active_goals = [g for g in goals_data[user_id]['goals'] if not g['completed']]
    completed_goals = [g for g in goals_data[user_id]['goals'] if g['completed']]
    
    message = "📚 *Your Study Goals*\n\n"
    
    if active_goals:
        message += "*🎯 Active Goals:*\n"
        for i, goal in enumerate(active_goals, 1):
            message += f"{i}. *{goal['subject'].upper()}*: {goal['goal']}\n"
        message += "\n"
    
    if completed_goals:
        message += "*✅ Recently Completed:*\n"
        for goal in completed_goals[-5:]:
            message += f"• *{goal['subject'].upper()}*: {goal['goal']}\n"
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Complete Goal", callback_data="complete_menu"),
            InlineKeyboardButton("🗑️ Delete Goal", callback_data="delete_menu")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(message, parse_mode='Markdown', reply_markup=reply_markup)

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    
    if query.data == "complete_menu":
        active_goals = [g for g in goals_data[user_id]['goals'] if not g['completed']]
        
        if not active_goals:
            await query.edit_message_text("No active goals to complete!")
            return
        
        keyboard = []
        for i, goal in enumerate(active_goals):
            keyboard.append([
                InlineKeyboardButton(
                    f"{goal['subject'].upper()}: {goal['goal'][:30]}...",
                    callback_data=f"complete_{i}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a goal to mark as completed:", reply_markup=reply_markup)
    
    elif query.data == "delete_menu":
        active_goals = [g for g in goals_data[user_id]['goals'] if not g['completed']]
        
        if not active_goals:
            await query.edit_message_text("No active goals to delete!")
            return
        
        keyboard = []
        for i, goal in enumerate(active_goals):
            keyboard.append([
                InlineKeyboardButton(
                    f"{goal['subject'].upper()}: {goal['goal'][:30]}...",
                    callback_data=f"delete_{i}"
                )
            ])
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Select a goal to delete:", reply_markup=reply_markup)
    
    elif query.data.startswith("complete_"):
        goal_index = int(query.data.split("_")[1])
        active_goals = [g for g in goals_data[user_id]['goals'] if not g['completed']]
        
        if goal_index < len(active_goals):
            goal = active_goals[goal_index]
            goal['completed'] = True
            goal['completed_date'] = datetime.now().strftime('%Y-%m-%d')
            save_goals(goals_data)
            
            await query.edit_message_text(
                f"🎉 Great job! Goal completed!\n\n"
                f"*{goal['subject'].upper()}*: {goal['goal']}",
                parse_mode='Markdown'
            )
    
    elif query.data.startswith("delete_"):
        goal_index = int(query.data.split("_")[1])
        active_goals = [g for g in goals_data[user_id]['goals'] if not g['completed']]
        
        if goal_index < len(active_goals):
            goal = active_goals[goal_index]
            goals_data[user_id]['goals'].remove(goal)
            save_goals(goals_data)
            
            await query.edit_message_text(
                f"🗑️ Goal deleted!\n\n"
                f"*{goal['subject'].upper()}*: {goal['goal']}",
                parse_mode='Markdown'
            )
    
    elif query.data == "cancel":
        await query.edit_message_text("Cancelled.")

async def set_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⏰ Usage: /setreminder <time>\n\n"
            "Example: /setreminder 09:00\n"
            "Use 24-hour format (HH:MM)"
        )
        return
    
    time_str = context.args[0]
    user_id = str(update.effective_user.id)
    
    try:
        datetime.strptime(time_str, '%H:%M')
        
        if user_id not in goals_data:
            goals_data[user_id] = {
                'goals': [],
                'reminder_time': time_str,
                'username': update.effective_user.first_name
            }
        else:
            goals_data[user_id]['reminder_time'] = time_str
        
        save_goals(goals_data)
        await update.message.reply_text(
            f"⏰ Daily reminders set for *{time_str}*\n"
            f"I'll send you a message with your active goals every day at this time!",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid time format!\n"
            "Please use HH:MM format (e.g., 09:00 or 14:30)"
        )

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in goals_data or not goals_data[user_id]['goals']:
        await update.message.reply_text(
            "No stats available yet! 📊\n"
            "Start adding goals with /addgoal"
        )
        return
    
    all_goals = goals_data[user_id]['goals']
    completed = [g for g in all_goals if g['completed']]
    active = [g for g in all_goals if not g['completed']]
    
    subjects = {}
    for goal in all_goals:
        subj = goal['subject'].capitalize()
        if subj not in subjects:
            subjects[subj] = {'total': 0, 'completed': 0}
        subjects[subj]['total'] += 1
        if goal['completed']:
            subjects[subj]['completed'] += 1
    
    completion_rate = (len(completed) / len(all_goals) * 100) if all_goals else 0
    
    message = "📊 *Your Study Statistics*\n\n"
    message += f"📚 Total Goals: *{len(all_goals)}*\n"
    message += f"✅ Completed: *{len(completed)}*\n"
    message += f"🎯 Active: *{len(active)}*\n"
    message += f"📈 Completion Rate: *{completion_rate:.1f}%*\n\n"
    
    if subjects:
        message += "*By Subject:*\n"
        for subj, data in subjects.items():
            message += f"• *{subj}*: {data['completed']}/{data['total']} completed\n"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def clear_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    
    if user_id not in goals_data:
        await update.message.reply_text("No history to clear!")
        return
    
    goals_data[user_id]['goals'] = [g for g in goals_data[user_id]['goals'] if not g['completed']]
    save_goals(goals_data)
    
    await update.message.reply_text("🧹 Cleared all completed goals!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """📖 *Study Bot Commands*

/start - Start the bot
/addgoal <subject> <goal> - Add a new study goal
/goals - View all your goals
/stats - View your study statistics
/setreminder <time> - Set daily reminder time (HH:MM)
/clearhistory - Clear completed goals
/help - Show this help message

*Examples:*
`/addgoal math Complete chapter 5 exercises`
`/addgoal physics Review Newton's laws`
`/setreminder 09:00`

Use /goals to view and manage your goals with buttons!"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def send_reminders(context: ContextTypes.DEFAULT_TYPE):
    now = datetime.now().strftime('%H:%M')
    
    for user_id, data in goals_data.items():
        if data.get('reminder_time') == now:
            active_goals = [g for g in data['goals'] if not g['completed']]
            
            if active_goals:
                message = "⏰ *Daily Study Reminder*\n\n"
                message += "Time to work on your goals! 💪\n\n"
                message += "*Your Active Goals:*\n"
                
                for i, goal in enumerate(active_goals[:5], 1):
                    message += f"{i}. *{goal['subject'].upper()}*: {goal['goal']}\n"
                
                message += "\nUse /goals to manage your goals!"
                
                try:
                    await context.bot.send_message(
                        chat_id=int(user_id),
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f'Could not send reminder to user {user_id}: {e}')

async def start_web_server(port):
    app = web.Application()
    app.router.add_get('/health', health_check)
    app.router.add_get('/', health_check)
    app.router.add_post('/webhook', webhook_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f'Web server running on port {port}')

async def main():
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    PORT = int(os.getenv('PORT', 10000))
    
    if not TOKEN:
        print('Error: TELEGRAM_BOT_TOKEN environment variable not set!')
        return
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("addgoal", add_goal))
    application.add_handler(CommandHandler("goals", view_goals))
    application.add_handler(CommandHandler("setreminder", set_reminder))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("clearhistory", clear_history))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CallbackQueryHandler(button_callback))
    
    job_queue = application.job_queue
    job_queue.run_repeating(send_reminders, interval=60, first=10)
    
    # Start web server for Render health checks
    asyncio.create_task(start_web_server(PORT))
    
    print(f'Bot is running on port {PORT}...')
    await application.initialize()
    await application.start()
    await application.updater.start_polling(allowed_updates=Update.ALL_TYPES)
    
    # Keep running
    await asyncio.Event().wait()

if __name__ == '__main__':
    asyncio.run(main())
