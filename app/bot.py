import asyncio
import logging
import os
import sqlite3
from datetime import datetime
from threading import Event, Thread

from dotenv import load_dotenv
from telegram import Bot, Update
from telegram.ext import Application, CallbackContext, CommandHandler

load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

TOKEN = os.getenv("TELEGRAM_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")
DAILY_REMINDER_START = "09:00:00"

# Database setup


def init_db():
    conn = sqlite3.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            description TEXT,
            category TEXT,
            deadline TEXT,
            completed BOOLEAN DEFAULT 0
        )
    """.strip()
    )

    conn.commit()
    conn.close()


# Command handlers


async def start_command(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to The Mighty To-Do List Bot!")


async def help_command(update: Update, context: CallbackContext):
    """
    Sends a message with all the available commands and their descriptions.
    """
    help_text = (
        "Here are the commands you can use with this bot:\n"
        "/start - Start interacting with the bot.\n"
        """/add - Add a new task. """
        """Usage: /add <description>; <category>; <deadline>\n"""
        "/list - List all your current tasks that are not yet completed.\n"
        "/delete - Delete a task. Usage: /delete <task_id>\n"
        "/complete - Mark a task as completed. Usage: /complete <task_id>\n"
        "/help - Show this help message."
    )
    await update.message.reply_text(help_text)


async def alarm(context: CallbackContext):
    """Check for tasks that are due and alarm the respective users."""
    try:
        job = context.job
        await context.bot.send_message(job.chat_id, text=job.data['message'])
        logging.info(
            f"Notified user {job.user_id} about task {job.data['task_id']}"
        )
    except Exception as e:
        logging.error(f"Unexpected error during alarm: {e}")


async def add_task(update: Update, context: CallbackContext):
    """
    Adds a new task to the database.
    Command format:
    /add <description>; <category>; <deadline: YYYY-MM-DD HH:MM>
    Example: /add Prepare presentation; work; 2023-10-15
    """
    try:
        args = " ".join(context.args).split(";")
        if len(args) != 3:
            await update.message.reply_text(
                """Usage:
                /add <description>; <category>; <deadline: YYYY-MM-DD HH:MM>
                """
            )
            return

        description = args[0].strip()
        category = args[1].strip()
        deadline_str = args[2].strip()

        try:
            deadline = datetime.strptime(deadline_str, '%Y-%m-%d %H:%M')
        except ValueError:
            await update.message.reply_text(
                "Invalid date format. Use YYYY-MM-DD HH:MM."
            )
            return

        now = datetime.now()
        if deadline <= now:
            await update.message.reply_text(
                "The deadline must be in the future."
            )
            return
        due = (deadline - now).total_seconds()

        user_id = update.effective_user.id

        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            """
        INSERT INTO tasks (user_id, description, category, deadline, completed)
        VALUES (?, ?, ?, ?, 0)
        """,
            (user_id, description, category, deadline_str),
        )
        task_id = cursor.lastrowid
        conn.commit()
        conn.close()

        context.job_queue.run_once(
            alarm,
            due,
            chat_id=update.effective_chat.id,
            user_id=user_id,
            data={
                'message': f"Reminder: Your task '{description}' is due now!",
                'task_id': str(task_id),
            },
            name=str(task_id),
        )

        await update.message.reply_text(f"Task {task_id} added successfully!")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text(
            "Failed to add task due to a database error."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await update.message.reply_text(
            "Failed to add task due to an unexpected error."
        )


async def delete_task(update: Update, context: CallbackContext):
    """
    Deletes a task from the database.
    Command format: /delete <task_id>
    Example: /delete 3
    """
    try:
        # Extracting the task ID from the command
        args = context.args
        if not args or not args[0].isdigit():
            await update.message.reply_text("Usage: /delete <task_id>")
            return

        task_id = int(args[0])
        user_id = update.effective_user.id

        # Database connection and deletion
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if the task belongs to the user
        cursor.execute(
            "SELECT id FROM tasks WHERE user_id = ? AND id = ?",
            (user_id, task_id),
        )
        task = cursor.fetchone()
        if not task:
            await update.message.reply_text(
                "Task not found or does not belong to you."
            )
            conn.close()
            return

        # If task found, delete it
        cursor.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        conn.commit()
        conn.close()

        # Remove alarm job from job queue
        current_jobs = context.job_queue.get_jobs_by_name(str(task_id))

        if not current_jobs:
            logging.warning(
                f"Failed to find and remove job {str(task_id)} in job queue"
            )
        for job in current_jobs:
            job.schedule_removal()
            logging.info(f"Removed job {str(task_id)} from job queue")

        await update.message.reply_text("Task deleted successfully!")
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text(
            "Failed to delete task due to a database error."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await update.message.reply_text(
            "Failed to delete task due to an unexpected error."
        )


async def mark_completed(update: Update, context: CallbackContext):
    """
    Marks a specified task as completed in the database.
    Command format: /complete <task_id>
    Example: /complete 42
    """
    try:
        # Extracting the task ID from the command
        args = context.args
        if not args or not args[0].isdigit():
            await update.message.reply_text("Usage: /complete <task_id>")
            return

        task_id = int(args[0])
        user_id = update.effective_user.id

        # Database connection and update
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()

        # Check if the task exists and belongs to the user
        cursor.execute(
            """
            SELECT id FROM tasks WHERE user_id = ? AND
            id = ? AND completed = FALSE
            """,
            (user_id, task_id),
        )
        task = cursor.fetchone()
        if not task:
            await update.message.reply_text(
                "Task not found or already completed."
            )
            conn.close()
            return

        # If task found and not completed, mark it as completed
        cursor.execute(
            "UPDATE tasks SET completed = TRUE WHERE id = ? AND user_id = ?",
            (task_id, user_id),
        )
        conn.commit()
        conn.close()

        await update.message.reply_text(
            "Task marked as completed successfully!"
        )
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text(
            "Failed to complete task due to a database error."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await update.message.reply_text(
            "Failed to complete task due to an unexpected error."
        )


async def list_tasks(update: Update, context: CallbackContext):
    """
    Lists the non-completed tasks of the user from the SQLite database.
    Command format: /list
    Example: /list
    """
    try:
        user_id = update.effective_user.id
        conn = sqlite3.connect(DATABASE_URL)
        c = conn.cursor()
        c.execute(
            """
            SELECT id, description, category, completed, deadline
            FROM tasks WHERE user_id=?
            ORDER BY completed, deadline
            """,
            (user_id,),
        )
        tasks = c.fetchall()
        message = None
        if tasks:
            message = (
                "id: description - category - completed - due by deadline\n"
            )
            message += "\n".join(
                f"{id}: {desc} - {cat} - {'True' if comp else 'False'}"
                + f" - due by {deadline}"
                for id, desc, cat, comp, deadline in tasks
            )
        await update.message.reply_text(
            message if message else "No tasks found."
        )
        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error: {e}")
        await update.message.reply_text(
            "Failed to list task due to a database error."
        )
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        await update.message.reply_text(
            "Failed to list task due to an unexpected error."
        )


async def notify_due_tasks(bot):
    """
    Check for tasks that will are due within the next 24
    hours and notify the respective users.
    """
    try:
        conn = sqlite3.connect(DATABASE_URL)
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, user_id, description
            FROM tasks
            WHERE deadline >= datetime('now', 'localtime')
            AND deadline < datetime('now', 'localtime', '+24 hours')
            AND completed = 0
            """
        )
        due_tasks = cursor.fetchall()

        for task_id, user_id, description in due_tasks:
            message = f"""
                Reminder: Task '{description}' is due in 24 hours!
                """.strip()
            await bot.send_message(chat_id=user_id, text=message)
            logging.info(f"Notified user {user_id} about task {task_id}")

        conn.close()
    except sqlite3.Error as e:
        logging.error(f"Database error during notification: {e}")
    except Exception as e:
        logging.error(f"Unexpected error during notification: {e}")


shutdown_event = Event()


def run_notifiers():
    """Run the scheduler loop to check for due tasks."""
    bot = Bot(token=TOKEN)
    reminded_today = False

    while not shutdown_event.is_set():
        now = datetime.now()
        reminder_start = datetime.strptime(
            f"{now.date().strftime('%Y-%m-%d')} {DAILY_REMINDER_START}",
            "%Y-%m-%d %H:%M:%S",
        )

        if reminder_start <= now and not reminded_today:
            reminded_today = True
            asyncio.run(notify_due_tasks(bot))
        elif reminder_start > now:
            reminded_today = False

        shutdown_event.wait(timeout=60)


# Main function


def main():
    """Run bot."""
    try:
        init_db()
        application = Application.builder().token(TOKEN).build()

        application.add_handler(CommandHandler("start", start_command))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(CommandHandler("add", add_task))
        application.add_handler(CommandHandler("list", list_tasks))
        application.add_handler(CommandHandler("delete", delete_task))
        application.add_handler(CommandHandler("complete", mark_completed))

        # Start the notifiers in a separate thread
        thread = Thread(target=run_notifiers)
        thread.start()

        # Run the bot until the user presses Ctrl-C
        application.run_polling(allowed_updates=Update.ALL_TYPES)

        # Shut down
        logging.info("Shutting down. This might take a moment.")
        shutdown_event.set()
        thread.join()
        logging.info("done.")
    except Exception as e:
        logging.error(f"Unexpected error in main: {e}")


if __name__ == "__main__":  # pragma: no mutate
    main()
