from sqlalchemy import create_engine, Column, Integer, Text, Float, Boolean, exc, text, DateTime, VARCHAR
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy import and_, func
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime
import json, os

class DatabaseConfig:
    def __init__(self, host="localhost", database="avt", user="postgres", password="123456", port=5432):
        self.host = host
        self.database = database
        self.user = user
        self.password = password
        self.port = port
        
    def save_to_json(self, file_path='config.json'):
        if not os.path.exists(file_path):
            settings = {}
        else:
            with open(file_path, 'r') as json_file:
                settings = json.load(json_file)

        settings['database'] = {
            'host': self.host,
            'database': self.database,
            'user': self.user,
            'password': self.password,
            'port': self.port
        }
        
        with open(file_path, 'w') as json_file:
            json.dump(settings, json_file, indent=4)
        print(f"Database settings saved to {file_path}")

    @classmethod
    def read_from_json(cls, file_path='config.json'):
        if not os.path.exists(file_path):
            print(f"File {file_path} not found. Returning default settings.")
            return cls()
        
        with open(file_path, 'r') as json_file:
            settings = json.load(json_file)
        
        db_settings = settings.get('database', {})
        return cls(**db_settings)

Base = declarative_base()

class AvtTask(Base):
    __tablename__ = 'avt_task'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_type = Column(Integer, nullable=False)
    creator = Column(VARCHAR, nullable=True)
    task_param = Column(Text, nullable=True)
    task_stat = Column(Integer, nullable=True)
    worker_ip = Column(VARCHAR, nullable=True)
    process_id = Column(Integer, nullable=True)
    task_eta = Column(Integer, nullable=True)
    task_output = Column(Text, nullable=True)
    task_message = Column(VARCHAR, nullable=True)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)
    user_id = Column(Integer, nullable=True)
    task_id_ref = Column(Integer, nullable=True)

class TaskConfig(Base):
    __tablename__ = 'avt_task_config'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(VARCHAR, nullable=False, unique=True)
    type = Column(Integer, nullable=False)
    params = Column(Text, nullable=True)
    outputs = Column(Text, nullable=True)
    options = Column(Text, nullable=True)
    start_by = Column(VARCHAR, nullable=True)
    enable = Column(Boolean, nullable=True)
    content_html = Column(Text, nullable=True)
    order = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=True)

class Database:
    def __init__(self, host, port, user, password, db_name):
        self.db_url = self.create_db_url(host, port, user, password, db_name)
        self.engine = create_engine(self.db_url)
        self.Session = sessionmaker(bind=self.engine)
        self.connected = False
        try:
            self.test_connection()
            self.connected = True
        except Exception as e:
            print(f"Failed to connect to the database: {e}")

    @staticmethod
    def create_db_url(host, port, user, password, db_name):
        return f'postgresql://{user}:{password}@{host}:{port}/{db_name}'

    def add_task(self, task_type, creator, task_param=None, task_stat=None, worker_ip=None, process_id=None, task_eta=None, task_output=None, task_message=None, user_id=None, task_id_ref=None):
        session = self.Session()
        
        try:
            param_json = json.dumps(task_param) if (isinstance(task_param, list) or isinstance(task_param, dict)) else task_param
            
            new_task = AvtTask(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                task_type=task_type,
                creator=creator,
                task_param=param_json,
                task_stat=task_stat,
                worker_ip=worker_ip,
                process_id=process_id,
                task_eta=task_eta,
                task_output=task_output,
                task_message=task_message,
                user_id=user_id,
                task_id_ref=task_id_ref
            )
            session.add(new_task)
            session.commit()
            task_id = new_task.id
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error adding task: {e}")
            task_id = None
        finally:
            session.close()
        
        return task_id

    def update_task(self, task_id, **kwargs):
        session = self.Session()
        
        try:
            task = session.query(AvtTask).filter_by(id=task_id).first()
            if not task:
                return False
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updated_at = datetime.now()
            session.commit()
            success = True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating task: {e}")
            success = False
        finally:
            session.close()
        
        return success

    def get_first_waiting_task_by_type(self, task_type):
        session = self.Session()
        try:
            # Query to get tasks with task_stat < 0 and the specific task_type
            tasks_query = session.query(AvtTask).filter(
                and_(
                    AvtTask.task_stat < 0,
                    AvtTask.task_type == task_type
                )
            ).order_by(
                # Order by task_stat (closer to -1 is better)
                func.abs(AvtTask.task_stat - (-1)),
                # Then order by latest created_at
                AvtTask.created_at.desc()
            )

            # Fetch the first result
            task = tasks_query.first()

            if not task:
                # print(f"No tasks found for type {task_type} with task_stat < 0.")
                return None

            return task
        except SQLAlchemyError as e:
            print(f"Error retrieving task: {e}")
            return None
        finally:
            session.close()

    def get_task_by_id(self, task_id):
        session = self.Session()
        try:
            task = session.query(AvtTask).filter_by(id=task_id).first()
            if not task:
                print(f"Task with ID {task_id} not found.")
                return None
            return task
        except SQLAlchemyError as e:
            print(f"Error retrieving task by ID: {e}")
            return None
        finally:
            session.close()
    
    def get_tasks(self, limit=None, offset=None):
        session = self.Session()
        
        try:
            query = session.query(AvtTask).order_by(AvtTask.created_at.desc())
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            tasks = query.all()
        except SQLAlchemyError as e:
            print(f"Error retrieving tasks: {e}")
            tasks = []
        finally:
            session.close()
        
        return tasks

    def add_task_config(self, name, task_type, params=None, outputs=None, options=None, start_by=None, enable=True, content_html=None, order=None):
        session = self.Session()
        
        try:
            params_json = json.dumps(params) if (isinstance(params, list) or isinstance(params, dict)) else params
            outputs_json = json.dumps(outputs) if (isinstance(outputs, list) or isinstance(outputs, dict)) else outputs
            
            new_config = TaskConfig(
                created_at=datetime.now(),
                updated_at=datetime.now(),
                name=name,
                type=task_type,
                params=params_json,
                outputs=outputs_json,
                options=options,
                start_by=start_by,
                enable=enable,
                content_html=content_html,
                order=order
            )
            session.add(new_config)
            session.commit()
            config_id = new_config.id
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error adding task config: {e}")
            config_id = None
        finally:
            session.close()
        
        return config_id

    def update_task_config(self, config_id, **kwargs):
        session = self.Session()
        
        try:
            config = session.query(TaskConfig).filter_by(id=config_id).first()
            if not config:
                return False
            for key, value in kwargs.items():
                setattr(config, key, value)
            config.updated_at = datetime.now()
            session.commit()
            success = True
        except SQLAlchemyError as e:
            session.rollback()
            print(f"Error updating task config: {e}")
            success = False
        finally:
            session.close()
        
        return success

    def get_task_configs(self, limit=None, offset=None):
        session = self.Session()
        
        try:
            query = session.query(TaskConfig)
            if limit:
                query = query.limit(limit)
            if offset:
                query = query.offset(offset)
            configs = query.all()
        except SQLAlchemyError as e:
            print(f"Error retrieving task configs: {e}")
            configs = []
        finally:
            session.close()
        
        return configs
    
    def test_connection(self):
        try:
            with self.engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except exc.SQLAlchemyError as e:
            raise Exception(f"Database connection failed: {e}")
        
# Example usage
if __name__ == "__main__":

    db_config = DatabaseConfig().read_from_json("config.json")
    # print(db_config.host, db_config.port)
    db = Database(db_config.host, db_config.port, db_config.user, db_config.password, db_config.database)
    task = db.get_first_waiting_task_by_type(7)
    if task is not None:
        print("Task: ", task.id, task.task_id_ref)
    else:
        print("No waiting task to serve!")
    # db.update_task(5, creator="ThaiHocUpdated")

    