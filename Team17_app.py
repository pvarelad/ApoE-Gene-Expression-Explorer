import mariadb
import csv
import io 
from flask import Flask, request, render_template, jsonify, Response


app = Flask(__name__)

DB_HOST     = "bioed-new.bu.edu"
DB_USER     = "mmccar53"
DB_PASSWORD = "$parkleS0509"
DB_NAME     = "Team17"
DB_PORT     = 4253


def get_db():
    connection = mariadb.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        port=int(DB_PORT)
    )
    return connection


def query(sql, params=(), one=False):
    """Execute a query and return results as a list of dicts (or one dict)."""
    conn = get_db()
    cur = conn.cursor()
    cur.execute(sql, params)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    conn.close()
    return rows[0] if (one and rows) else rows

@app.route("/test_db")
def test_db():
    try:
        conn = mariadb.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME,
            port=int(DB_PORT)
        )
        cur = conn.cursor()
        cur.execute("SHOW TABLES;")
        tables = [row[0] for row in cur.fetchall()]
        cur.close()
        conn.close()
        return jsonify({
            "status": "connected",
            "database": DB_NAME,
            "tables": tables
        })
    except mariadb.OperationalError as e:
        return jsonify({"status": "error", "type": "OperationalError", "message": str(e)}), 500
    except mariadb.ProgrammingError as e:
        return jsonify({"status": "error", "type": "ProgrammingError", "message": str(e)}), 500
    except Exception as e:
        return jsonify({"status": "error", "type": type(e).__name__, "message": str(e)}), 500
    

@app.route("/api/download/de")
def download_de():
    comparison = request.args.get("comparison_group", "")
    fdr        = float(request.args.get("fdr_threshold", 0.05))
    logfc_min  = float(request.args.get("logfc_min", 0))
    direction  = request.args.get("direction", "both")

    direction_clause = ""
    if direction == "up":
        direction_clause = "AND de.logFC > 0"
    elif direction == "down":
        direction_clause = "AND de.logFC < 0"

    sql = f"""
        SELECT de.gene_id, g.gene_name, g.gene_type,
               de.logFC, de.logCPM, de.F, de.PValue, de.FDR
        FROM differential_expression de
        JOIN genes g ON de.gene_id = g.gene_id
        WHERE de.comparison_group = ?
          AND de.FDR <= ?
          AND ABS(de.logFC) >= ?
          {direction_clause}
        ORDER BY de.FDR ASC, ABS(de.logFC) DESC
    """
    rows = query(sql, (comparison, fdr, logfc_min))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["gene_id","gene_name","gene_type","logFC","logCPM","F","PValue","FDR"])
    for r in rows:
        writer.writerow([r["gene_id"],r["gene_name"],r["gene_type"],r["logFC"],r["logCPM"],r["F"],r["PValue"],r["FDR"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=DE_{comparison}.csv"}
    )


@app.route("/api/download/gene")
def download_gene():
    gene_id = request.args.get("gene_id", "")
    if not gene_id:
        return jsonify({"error": "gene_id required"}), 400

    sample_counts = query(
        """SELECT e.sample_id, e.count, s.condition, s.apoE_genotype, s.exon_status
           FROM expression_counts e
           JOIN samples s ON e.sample_id = s.sample_id
           WHERE e.gene_id = ?
           ORDER BY s.apoE_genotype, s.exon_status, e.sample_id""",
        (gene_id,)
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["sample_id","count","condition","apoE_genotype","exon_status"])
    for r in sample_counts:
        writer.writerow([r["sample_id"],r["count"],r["condition"],r["apoE_genotype"],r["exon_status"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=gene_{gene_id}_counts.csv"}
    )


# ── NEW: Download DE results for a specific gene across all comparisons ───────

@app.route("/api/download/gene_de")
def download_gene_de():
    gene_id = request.args.get("gene_id", "")
    if not gene_id:
        return jsonify({"error": "gene_id required"}), 400

    rows = query(
        """SELECT de.comparison_group, c.condition_1, c.condition_2,
                  de.logFC, de.logCPM, de.F, de.PValue, de.FDR
           FROM differential_expression de
           JOIN comparisons c ON de.comparison_group = c.comparison_group
           WHERE de.gene_id = ?
           ORDER BY de.FDR""",
        (gene_id,)
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["comparison_group","condition_1","condition_2","logFC","logCPM","F","PValue","FDR"])
    for r in rows:
        writer.writerow([
            r["comparison_group"], r["condition_1"], r["condition_2"],
            r["logFC"], r["logCPM"], r["F"], r["PValue"], r["FDR"]
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename=gene_{gene_id}_DE.csv"}
    )


@app.route("/api/download/de_by_group")
def download_de_by_group():
    apoe      = request.args.get("apoe_genotype", "all")
    exon      = request.args.get("exon_status", "all")
    fdr       = float(request.args.get("fdr_threshold", 0.05))
    logfc_min = float(request.args.get("logfc_min", 1))
    direction = request.args.get("direction", "both")

    conditions = ["de.FDR <= ?", "ABS(de.logFC) >= ?"]
    params = [fdr, logfc_min]

    if apoe == "e3/e3":
        conditions.append("(de.comparison_group LIKE '%a3%')")
    elif apoe == "e4/e4":
        conditions.append("(de.comparison_group LIKE '%a4%')")

    if exon == "ex19":
        conditions.append("(de.comparison_group LIKE '%c%')")
    elif exon == "Dex19":
        conditions.append("(de.comparison_group LIKE '%d%')")

    if direction == "up":
        conditions.append("de.logFC > 0")
    elif direction == "down":
        conditions.append("de.logFC < 0")

    where = "WHERE " + " AND ".join(conditions)

    sql = f"""
        SELECT de.gene_id, g.gene_name, g.gene_type,
               de.comparison_group, de.logFC, de.logCPM, de.F, de.PValue, de.FDR
        FROM differential_expression de
        JOIN genes g ON de.gene_id = g.gene_id
        {where}
        ORDER BY de.FDR ASC, ABS(de.logFC) DESC
    """
    rows = query(sql, tuple(params))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["gene_id","gene_name","gene_type","comparison_group","logFC","logCPM","F","PValue","FDR"])
    for r in rows:
        writer.writerow([r["gene_id"],r["gene_name"],r["gene_type"],r["comparison_group"],r["logFC"],r["logCPM"],r["F"],r["PValue"],r["FDR"]])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=DE_by_group.csv"}
    )


# ── Pages ─────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


# ── API: Overview Stats ───────────────────────────────────────────────────────

@app.route("/api/stats/overview")
def overview_stats():
    try:
        total_genes       = query("SELECT COUNT(*) AS n FROM genes", one=True)["n"]
        total_samples     = query("SELECT COUNT(*) AS n FROM samples", one=True)["n"]
        total_comparisons = query("SELECT COUNT(DISTINCT comparison_group) AS n FROM differential_expression", one=True)["n"]
        sig_de_pairs      = query("SELECT COUNT(*) AS n FROM differential_expression WHERE FDR <= 0.05", one=True)["n"]
        return jsonify({
            "total_genes": total_genes,
            "total_samples": total_samples,
            "total_comparisons": total_comparisons,
            "sig_de_pairs": sig_de_pairs
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: Gene Search & Detail ─────────────────────────────────────────────────

@app.route("/api/gene/search")
def gene_search():
    q = request.args.get("q", "").strip()
    if len(q) < 2:
        return jsonify([])
    try:
        rows = query(
            "SELECT gene_id, gene_name, gene_type FROM genes WHERE gene_name LIKE ? OR gene_id LIKE ? LIMIT 20",
            (f"%{q}%", f"%{q}%")
        )
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/gene/<gene_id>")
def gene_detail(gene_id):
    try:
        gene = query("SELECT * FROM genes WHERE gene_id = ?", (gene_id,), one=True)
        if not gene:
            return jsonify({"error": "Gene not found"}), 404

        de_results = query(
            """SELECT de.comparison_group, c.condition_1, c.condition_2,
                      de.logFC, de.logCPM, de.F, de.PValue, de.FDR
               FROM differential_expression de
               JOIN comparisons c ON de.comparison_group = c.comparison_group
               WHERE de.gene_id = ?
               ORDER BY de.FDR""",
            (gene_id,)
        )

        # Mean counts with SEM (standard error of the mean = STDDEV / SQRT(N))
        mean_counts = query(
            """SELECT s.apoE_genotype, s.exon_status, s.condition,
                      ROUND(AVG(e.count), 2) AS mean_count,
                      ROUND(STDDEV(e.count), 2) AS std_dev,
                      COUNT(*) AS n_samples,
                      ROUND(STDDEV(e.count) / SQRT(COUNT(*)), 2) AS sem
               FROM expression_counts e
               JOIN samples s ON e.sample_id = s.sample_id
               WHERE e.gene_id = ?
               GROUP BY s.apoE_genotype, s.exon_status, s.condition
               ORDER BY s.apoE_genotype, s.exon_status, s.condition""",
            (gene_id,)
        )

        sample_counts = query(
            """SELECT e.sample_id, e.count, s.condition, s.apoE_genotype, s.exon_status
               FROM expression_counts e
               JOIN samples s ON e.sample_id = s.sample_id
               WHERE e.gene_id = ?
               ORDER BY s.apoE_genotype, s.exon_status, e.sample_id""",
            (gene_id,)
        )

        return jsonify({
            "gene": gene,
            "de_results": de_results,
            "mean_counts": mean_counts,
            "sample_counts": sample_counts
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: DE Explorer ──────────────────────────────────────────────────────────

@app.route("/api/de/comparisons")
def list_comparisons():
    try:
        rows = query("SELECT * FROM comparisons ORDER BY comparison_group")
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/de/top")
def top_de_genes():
    comparison = request.args.get("comparison_group", "")
    fdr        = float(request.args.get("fdr_threshold", 0.05))
    logfc_min  = float(request.args.get("logfc_min", 0))
    direction  = request.args.get("direction", "both")
    limit      = int(request.args.get("limit", 20))

    if not comparison:
        return jsonify({"error": "comparison_group is required"}), 400

    direction_clause = ""
    if direction == "up":
        direction_clause = "AND de.logFC > 0"
    elif direction == "down":
        direction_clause = "AND de.logFC < 0"

    try:
        sql = f"""
            SELECT de.gene_id, g.gene_name, g.gene_type,
                   de.logFC, de.logCPM, de.F, de.PValue, de.FDR
            FROM differential_expression de
            JOIN genes g ON de.gene_id = g.gene_id
            WHERE de.comparison_group = ?
              AND de.FDR <= ?
              AND ABS(de.logFC) >= ?
              {direction_clause}
            ORDER BY de.FDR ASC, ABS(de.logFC) DESC
            LIMIT ?
        """
        rows = query(sql, (comparison, fdr, logfc_min, limit))
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── API: DE by Genotype/Exon Group ───────────────────────────────────────────

@app.route("/api/de/by_group")
def de_by_group():
    apoe      = request.args.get("apoe_genotype", "all")
    exon      = request.args.get("exon_status", "all")
    fdr       = float(request.args.get("fdr_threshold", 0.05))
    logfc_min = float(request.args.get("logfc_min", 1))
    direction = request.args.get("direction", "both")
    limit     = int(request.args.get("limit", 30))

    conditions = ["de.FDR <= ?", "ABS(de.logFC) >= ?"]
    params = [fdr, logfc_min]

    # Filter comparison groups by ApoE genotype
    if apoe == "e3/e3":
        conditions.append("(de.comparison_group LIKE '%a3%')")
    elif apoe == "e4/e4":
        conditions.append("(de.comparison_group LIKE '%a4%')")

    # Filter comparison groups by exon status
    if exon == "ex19":
        conditions.append("(de.comparison_group LIKE '%c%')")
    elif exon == "Dex19":
        conditions.append("(de.comparison_group LIKE '%d%')")

    # Direction filter
    if direction == "up":
        conditions.append("de.logFC > 0")
    elif direction == "down":
        conditions.append("de.logFC < 0")

    where = "WHERE " + " AND ".join(conditions)

    try:
        sql = f"""
            SELECT de.gene_id, g.gene_name, g.gene_type,
                   de.comparison_group, de.logFC, de.logCPM, de.F, de.PValue, de.FDR
            FROM differential_expression de
            JOIN genes g ON de.gene_id = g.gene_id
            {where}
            ORDER BY de.FDR ASC, ABS(de.logFC) DESC
            LIMIT ?
        """
        params.append(limit)
        rows = query(sql, tuple(params))
        return jsonify(rows)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
