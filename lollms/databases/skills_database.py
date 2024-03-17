import sqlite3
from safe_store.text_vectorizer import TextVectorizer, VectorizationMethod, VisualizationMethod
import numpy as np
class SkillsLibrary:
        
    def __init__(self, db_path):
        self.db_path =db_path
        self._initialize_db()
       

    def _initialize_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_library (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                category TEXT,
                title TEXT,
                content TEXT
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS db_info (
                version INTEGER
            )
        """)
        cursor.execute("SELECT version FROM db_info")
        version = cursor.fetchone()
        self._create_fts_table()  # Create FTS table after initializing the database
        if version is None:
            cursor.execute("INSERT INTO db_info (version) VALUES (1)")
            conn.commit()
            cursor.close()
            conn.close()
        else:
            cursor.close()
            conn.close()
            self._migrate_db(version[0])

    def _create_fts_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS skills_library_fts USING fts5(category, title, content)
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def _migrate_db(self, version):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        # Perform migrations based on the current version
        # For example, if the current version is 1 and the latest version is 2:
        if version < 2:
            cursor.execute("ALTER TABLE skills_library ADD COLUMN new_column TEXT")
            cursor.execute("UPDATE db_info SET version = 2")
            conn.commit()
        cursor.close()
        conn.close()

    def _create_table(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills_library (
                id INTEGER PRIMARY KEY,
                version INTEGER,
                category TEXT,
                title TEXT,
                content TEXT
            )
        """)
        conn.commit()
        cursor.close()
        conn.close()

    def add_entry(self, version, category, title, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("""
            INSERT INTO skills_library (version, category, title, content) 
            VALUES (?, ?, ?, ?)
        """, (version, category, title, content))
        conn.commit()
        cursor.close()
        conn.close()

    def list_entries(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("SELECT * FROM skills_library")
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return res
    
    def query_entry(self, text):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("""
            SELECT * FROM skills_library 
            WHERE category LIKE ? OR title LIKE ? OR content LIKE ?
        """, (f'%{text}%', f'%{text}%', f'%{text}%'))
        res= cursor.fetchall()
        cursor.close()
        conn.close()
        return res
    
    def query_entry_fts(self, text):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT * FROM skills_library_fts WHERE skills_library_fts MATCH ?"
        cursor.execute(query, (text,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return res

    def query_vector_db(self, query_, top_k=3, max_dist=1000):
        vectorizer = TextVectorizer(VectorizationMethod.TFIDF_VECTORIZER)
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT id, title FROM skills_library"
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        skills = []
        if len(res)>0:
            for entry in res:
                vectorizer.add_document(entry[0],entry[1])
            vectorizer.index()
            
            skill_titles, sorted_similarities, document_ids = vectorizer.recover_text(query_, top_k)
            for skill_title, sim, id in zip(skill_titles, sorted_similarities, document_ids):
                if  np.linalg.norm(sim[1])<max_dist:
                    conn = sqlite3.connect(self.db_path)
                    cursor = conn.cursor()
                    # Use direct string concatenation for the MATCH expression.
                    # Ensure text is safely escaped to avoid SQL injection.
                    query = "SELECT content FROM skills_library WHERE id = ?"
                    cursor.execute(query, (id,))
                    res = cursor.fetchall()
                    skills.append(res[0])
                    cursor.close()
                    conn.close()
        else:
            skill_titles = []
        return skill_titles, skills

    
    def dump(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT * FROM skills_library"
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [[r[0], r[1], r[2], r[3]] for r in res]

    def get_categories(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT category FROM skills_library"
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return list(set([r[0] for r in res]))
    
   
    def get_titles(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT id, title FROM skills_library"
        cursor.execute(query)
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id":r[0], "title":r[1]} for r in res]

    def get_titles_by_category(self, category):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT id, title FROM skills_library WHERE category=?"
        cursor.execute(query,(category,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id":r[0], "title":r[1]} for r in res]

    def get_content(self, id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT content FROM skills_library WHERE id = ?"
        cursor.execute(query, (id,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [r[0] for r in res]

    def get_skill(self, id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "SELECT id, category, title, content FROM skills_library WHERE id = ?"
        cursor.execute(query, (id,))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id":r[0], "category":r[1], "title":r[2], "content":r[3]} for r in res]

    def update_skill(self, id, category, title, content):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        # Use direct string concatenation for the MATCH expression.
        # Ensure text is safely escaped to avoid SQL injection.
        query = "UPDATE skills_library SET category=?, title=?, content=? WHERE id = ?"
        cursor.execute(query, (category,title,content))
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return [{"id":r[0], "category":r[1], "title":r[2], "content":r[3]} for r in res]


    def remove_entry(self, id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()        
        cursor.execute("DELETE FROM skills_library WHERE id = ?", (id,))
        conn.commit()
        cursor.close()
        conn.close()

    def export_entries(self, file_path):
        with open(file_path, 'w') as f:
            for entry in self.list_entries():
                f.write(f'{entry}\n')

    def import_entries(self, file_path):
        with open(file_path, 'r') as f:
            for line in f:
                entry = line.strip().split(',')
                self.add_entry(*entry)

    def fuse_with_another_db(self, other_db_path):
        other_conn = sqlite3.connect(other_db_path)
        other_cursor = other_conn.cursor()
        other_cursor.execute("SELECT * FROM skills_library")
        for row in other_cursor.fetchall():
            self.add_entry(*row[1:])  # skip the id column
