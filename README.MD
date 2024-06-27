# Simple Template Matching SAT Module

## Module Workflow

The Simple Template Matching SAT Module performs the following steps:

1. **Retrieve Task Parameters**: Fetch `avt_task_id` and `connection_url` from the runtime arguments.
   
2. **Fetch Function Parameters**: Retrieve main image and template image paths for the task from the database using `avt_task_id`.

3. **Download Images**: Download the main image and template image files from the FTP server to the local environment.

4. **Process Images**: Perform image processing on the downloaded images using the retrieved function parameters.

5. **Upload Results**: Upload the processed image results back to the FTP server.

6. **Update Task Status**: Update `task_stat` and `task_output` fields in the database for the specified `avt_task_id` to reflect the module's processing status.

7. **Exit Module**: Finish execution with an appropriate exit code (`EXIT_FINISHED = 0` for successful completion, or other codes for errors).

## Pre-defined Exit Codes

The module uses pre-defined exit codes to indicate different scenarios:

- `EXIT_FINISHED` : "Finished",
- `EXIT_GENERAL_ERROR` : "Miscellaneous errors, such as divide by zero and other impermissible operations",
- `EXIT_MISUSE_OF_SHELL_BUILT_IN` : "Missing keyword or command, or permission problem (and diff return code on a failed binary file comparison).",
- `EXIT_COMMAND_CANNOT_EXCUTE` : "Permission problem or command is not an executable",
- `EXIT_COMMAND_NOT_FOUND` : "Possible problem with $PATH or a typo",
- `EXIT_INVALID_ARGUMENT_EXIT_CODE` : "Exit takes only integer args in the range 0 - 255 (see first footnote)",
- `EXIT_SCRIPT_TERMINATED_BY_CONTROLC` : "	Control-C is fatal error signal 2, (130 = 128 + 2)",
- `EXIT_CANNOT_CONNECT_TO_DATABASE` : "Cannot connect to the database",
- `EXIT_INVALID_INPUT_AVT_TASK_ID` : "Invalid input task id",
- `EXIT_INVALID_MODULE_PARAMETERS` : "Invalid module parameters",
- `EXIT_FTP_DOWNLOAD_ERROR` : "FTP download error",
- `EXIT_FTP_UPLOAD_ERROR` : "FTP upload error",
- `EXIT_PROCESS_KILLED_BY_WTM` : "Process killed by WTM",
- `EXIT_OTHERS_ERROR` : "Others error" .

**Example Usage of Exit Codes**

```python
import sys
from database import Database  # Import Database class from your module
from exit_code import *

# Example usage to handle connection errors
db = Database(connection_url)
if not db.connected:
    print("Cannot connect to the database")
    sys.exit(EXIT_CANNOT_CONNECT_TO_DATABASE)
else:
    print("Successfully connected to the database!")

# Example usage to handle invalid task ID
task = db.get_task_by_id(avt_task_id)
if task is None:
    print("Cannot find task by ID")
    sys.exit(EXIT_INVALID_INPUT_AVT_TASK_ID)
```

## Development
**Create Database config and FTP server config file named config.json (default) file with format:**
```json
{
    "database": {
        "host": "localhost",
        "database": "avtdb",
        "user": "postgres",
        "password": "dbpassword",
        "port": 5443
    },
    "ftp": {
        "host": "localhost",
        "port": 21,
        "user": "username",
        "password": "password"
    }
}
```
**Run the project:**
```bash
pip install -r requirements.txt
python main.py
```

## Deployment
### Build the Executable
Deploy the module using `pyinstaller` to create a standalone executable:
```bash
pyinstaler --onefile main.py
```

###  Run the Excutable
```bash
/path/to/deploy/file --avt_task_id TASK_ID --connection_url CONN_URL --config_file PATH_TO_CONFIG_JSON_FILE
```
Replace TASK_ID and CONN_URL and PATH_TO_CONFIG_JSON_FILE with actual values specific to your environment.

## Configuration
Ensure to configure the following in `config.json` file:
- Database connection details (connection_url).
- FTP server credentials (server address, port, username, password).

# License
This project is licensed under a private license. Unauthorized copying or distribution of the code, or any part of it, is strictly prohibited.

# Authors
- Thai Hoc - Dev
- AVT project development team