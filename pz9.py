import psycopg2

class SQL:
    def __init__(self, **config):
        self.con = psycopg2.connect(**config)
        self.cur = self.con.cursor()
        self._reset()
    
    def _reset(self):
        self._cols, self._table, self._joins = "*", "", []
        self._where, self._params = "", ()
        self._order = ""
    
    def select(self, *cols):
        self._cols = ", ".join(cols) if cols else "*"
        return self
    
    def from_(self, table):
        self._table = table
        return self
    
    def where(self, cond, *params):
        self._where, self._params = f"WHERE {cond}", params
        return self
    
    def order_by(self, col, direction="ASC"):
        self._order = f"ORDER BY {col} {direction}"
        return self
    
    def join(self, table, on, type="INNER"):
        self._joins.append(f"{type} JOIN {table} ON {on}")
        return self
    
    def left_join(self, table, on):
        return self.join(table, on, "LEFT")
    
    def right_join(self, table, on):
        return self.join(table, on, "RIGHT")
    
    def full_join(self, table, on):
        return self.join(table, on, "FULL OUTER")
    
    def union(self, query):
        return f"{self.build()[0]} UNION {query}"
    
    def build(self):
        sql = f"SELECT {self._cols} FROM {self._table}"
        if self._joins: sql += " " + " ".join(self._joins)
        if self._where: sql += f" {self._where}"
        if self._order: sql += f" {self._order}"
        return sql, self._params
    
    def execute(self):
        sql, params = self.build()
        self.cur.execute(sql, params)
        self.con.commit()
        result = self.cur.fetchall()
        self._reset()
        return result
    
    def fetch(self):
        sql, params = self.build()
        self.cur.execute(sql, params)
        cols = [d[0] for d in self.cur.description]
        rows = self.cur.fetchall()
        self._reset()
        return [dict(zip(cols, r)) for r in rows]
    
    def insert(self, **values):
        cols = ", ".join(values.keys())
        placeholders = ", ".join(["%s"] * len(values))
        sql = f"INSERT INTO {self._table} ({cols}) VALUES ({placeholders}) RETURNING id"
        self.cur.execute(sql, tuple(values.values()))
        self.con.commit()
        return self.cur.fetchone()[0]
    
    def update(self, **values):
        set_clause = ", ".join([f"{k} = %s" for k in values.keys()])
        sql = f"UPDATE {self._table} SET {set_clause} {self._where}"
        self.cur.execute(sql, tuple(values.values()) + self._params)
        self.con.commit()
        rows = self.cur.rowcount
        self._reset()
        return rows
    
    def delete(self):
        sql = f"DELETE FROM {self._table} {self._where}"
        self.cur.execute(sql, self._params)
        self.con.commit()
        rows = self.cur.rowcount
        self._reset()
        return rows
    
    def close(self):
        self.cur.close()
        self.con.close()


db = SQL(host="localhost", database="mydb", user="admin", password="12345")
db.cur.execute("SET search_path TO online_cinema")

users = db.select("*").from_("users").fetch()
print(f"Всего пользователей {len(users)}")

filtUsers = db.select("id", "name").from_("users").where("id > 1").fetch()
print(f"Пользователей с id > 1 - {len(filtUsers)}")

ordered = db.select("*").from_("users").order_by("id", "DESC").fetch()
print(f"Все пользователи в порядке убывания id: {ordered}")

newId = db.from_("users").insert(id=700, name="TestUser", subscription_id=1)
print(f"Создан пользователь - {newId}")

updatedRows = db.from_("users").where("id = 700").update(subscription_id=2)
print(f"Обновлено строк: {updatedRows}")

deletedRows = db.from_("users").where("id = 700").delete()
print(f"Удалено строк: {deletedRows}")

a = (db
    .select("u.name", "s.name as sub_name", "s.price")
    .from_("users u")
    .left_join("subscriptions s", "u.subscription_id = s.id")
    .order_by("u.id")
    .fetch()
)
print(f"Join - {len(a)} записей")

q1, _ = db.select("title").from_("content_type").build()
q2, _ = db.select("title").from_("genres").build()
union = db.select("title").from_("content_type").union(q2)
db.cur.execute(union)
unionResult = db.cur.fetchall()
print(f"Union - {len(unionResult)} записей")

db.close()
