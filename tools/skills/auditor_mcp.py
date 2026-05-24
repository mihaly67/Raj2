from mcp.server.fastmcp import FastMCP
import os
import sqlite3

# Inicializáljuk a butított MCP szervert
mcp = FastMCP("ICA_Zero_Trust_Auditor")

# SZIGORÚ BÖRTÖN: Csak ebből a mappából olvashat!
ALLOWED_AUDIT_DIR = "/home/misi/Jules_ICA_Auditor/vps_logs"

def is_safe_path(filepath: str) -> bool:
    """Megakadályozza a Directory Traversal (../) támadásokat."""
    abs_path = os.path.abspath(os.path.join(ALLOWED_AUDIT_DIR, filepath))
    return abs_path.startswith(os.path.abspath(ALLOWED_AUDIT_DIR))

@mcp.tool()
def read_audit_log(filename: str, lines: int = 200) -> str:
    """
    KIZÁRÓLAG naplófájlok (pl. monitor.log, agent_memory.jsonl) olvasására szolgál.
    """
    if not is_safe_path(filename):
        return f"❌ BIZTONSÁGI BLOKKOLÁS: Nincs jogosultságod olvasni ezt a fájlt: {filename}"

    full_path = os.path.join(ALLOWED_AUDIT_DIR, filename)

    if not os.path.exists(full_path):
        return f"Hiba: A fájl nem található a szinkronizált mappában ({filename})."

    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = f.readlines()
            # Csak az utolsó X sort adjuk vissza, hogy ne terheljük túl a kontextust
            return "".join(content[-lines:])
    except Exception as e:
        return f"Olvasási hiba: {e}"

@mcp.tool()
def query_telemetry_db(query: str = "SELECT * FROM mcp_logs ORDER BY id DESC LIMIT 50") -> str:
    """
    Csak olvasható SQL lekérdezés a letöltött telemetria adatbázisból (mcp_telemetry.db).
    VIGYÁZAT: Az INSERT, UPDATE, DELETE parancsok tiltva vannak.
    """
    # Egyszerű bemenet-szűrés a tiltott műveletekre
    upper_query = query.upper()
    if any(forbidden in upper_query for forbidden in ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE"]):
        return "❌ BIZTONSÁGI BLOKKOLÁS: Csak SELECT parancsok engedélyezettek az Auditor számára!"

    db_path = os.path.join(ALLOWED_AUDIT_DIR, "mcp_telemetry.db")

    if not os.path.exists(db_path):
        return "Hiba: Az mcp_telemetry.db nem található. Futtattad a szinkronizáló szkriptet?"

    try:
        # A 'ro' (Read-Only) URI paraméter garantálja, hogy az SQLite ne engedjen írást
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()

        # Oszlopnevek kinyerése a tisztább eredmény érdekében
        column_names = [description[0] for description in cursor.description]

        result = f"Oszlopok: {', '.join(column_names)}\n"
        result += "-" * 50 + "\n"
        for row in rows:
            result += str(row) + "\n"

        conn.close()
        return result if rows else "A lekérdezés nem hozott eredményt."
    except sqlite3.Error as e:
        return f"Adatbázis hiba (Lehet, hogy hibás a szintaxis?): {e}"

if __name__ == "__main__":
    mcp.run()
