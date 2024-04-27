# The-Mighty-Todolist-Telegram-Bot

## Prepare Dev Environment

1) Install Dependencies:

    Use poetry as an environment and module manager to install dependencies by:

    ```bash
    poetry install
    ```

2) Add Environment Variables:

    Create `.env` file in project working directory. The env file will provide the needed environment variables to python files.

    ```bash
    echo "TELEGRAM_TOKEN=THE_REAL_TOKEN" > .env
    ```

3) Link Pre-Commit Hook:

    Link pre-commit hook to your `.git` file to format *python* files using *black* and *autopep8*.

    ```bash
    ln pre-commit .git/hooks/pre-commit
    ```
