"""
Scientific Analytics & Knowledge Graph Service Layer.

Demonstrates:
- Part 14 (NumPy): Vectorized quiz score arrays, moving averages, percentiles, standard deviation
- Part 15 (SciPy): Linear regression (`scipy.stats.linregress`), Z-scores (`scipy.stats.zscore`),
  Normal distribution PDF/CDF (`scipy.stats.norm`), and Pearson correlation (`scipy.stats.pearsonr`)
- Part 16 (Matplotlib): Theme-matched study analytics charts rendered to base64 PNG
- Part 17 (NetworkX): Knowledge Map graph connecting Subjects -> Topics -> Notes with centrality metrics
- Part 22 (OOP): AnalyticsManager encapsulating scientific computation and visualization
"""
import base64
import io
from datetime import timedelta
from typing import Any, Dict, List
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
from scipy import stats
from django.utils import timezone
from notes.models import Note, Subject
from progress.models import StudyLog
from progress.services import ProgressTracker
from quizzes.models import Quiz
from tasks.models import Task


class AnalyticsManager:
    """
    OOP Manager for numerical analysis (NumPy), statistical inference (SciPy),
    chart generation (Matplotlib), and Knowledge Graph construction (NetworkX).
    """

    # Color Palette from Specification (Part 3)
    COLOR_PRIMARY_ROSE = "#C17876"
    COLOR_DARK_BURGUNDY = "#853737"
    COLOR_SECONDARY_ROSE = "#B26766"
    COLOR_DARK_SECONDARY = "#944747"
    COLOR_SURFACE_CREAM = "#FAF5F4"
    COLOR_CARD_BG = "#FFFDFC"
    COLOR_TEXT_DARK = "#3A1D1D"
    COLOR_MUTED_ROSE = "#E6C8C7"

    # ==========================================================
    # PART 14: NUMPY NUMERICAL ANALYSIS
    # ==========================================================
    @classmethod
    def compute_numpy_metrics(cls) -> Dict[str, Any]:
        """
        Perform vectorized numerical analysis using NumPy on quiz scores,
        note word counts, and daily study durations.
        """
        quiz_percentages = list(
            Quiz.objects.filter(completed=True)
            .order_by("created_at", "id")
            .values_list("percentage", flat=True)
        )
        scores_arr = (
            np.array(quiz_percentages, dtype=np.float64)
            if quiz_percentages
            else np.array([0.0], dtype=np.float64)
        )

        # Cumulative moving average using NumPy vector operations
        indices = np.arange(1, len(scores_arr) + 1, dtype=np.float64)
        moving_averages = np.round(np.cumsum(scores_arr) / indices, 2)

        # Percentiles and spread
        p25, p50, p75, p90 = np.round(np.percentile(scores_arr, [25, 50, 75, 90]), 2)

        # Note word count array analysis
        note_lengths = [len((c or "").split()) for c in Note.objects.values_list("content", flat=True)]
        lengths_arr = np.array(note_lengths if note_lengths else [0], dtype=np.float64)

        # Study minutes array analysis
        study_mins = list(StudyLog.objects.order_by("date").values_list("study_minutes", flat=True))
        mins_arr = np.array(study_mins if study_mins else [0], dtype=np.float64)

        return {
            "quiz_scores_array": scores_arr.round(1).tolist(),
            "moving_average_array": moving_averages.tolist(),
            "mean_score": float(np.round(np.mean(scores_arr), 2)),
            "median_score": float(p50),
            "std_dev_score": float(np.round(np.std(scores_arr), 2)),
            "variance_score": float(np.round(np.var(scores_arr), 2)),
            "min_score": float(np.round(np.min(scores_arr), 2)),
            "max_score": float(np.round(np.max(scores_arr), 2)),
            "percentile_25": float(p25),
            "percentile_75": float(p75),
            "percentile_90": float(p90),
            "avg_note_words": float(np.round(np.mean(lengths_arr), 1)),
            "total_note_words": int(np.sum(lengths_arr)),
            "avg_daily_study_minutes": float(np.round(np.mean(mins_arr), 1)),
            "total_study_minutes": int(np.sum(mins_arr)),
        }

    # ==========================================================
    # PART 15: SCIPY STATISTICAL ANALYSIS
    # ==========================================================
    @classmethod
    def compute_scipy_statistics(cls) -> Dict[str, Any]:
        """
        Perform statistical analysis using `scipy.stats`:
        1. Linear regression (`stats.linregress`) on quiz scores over time to detect learning trajectory
        2. Standardized Z-scores (`stats.zscore`) to identify outlier performances
        3. Normal distribution modeling (`stats.norm`) for mastery probability above 80%
        4. Pearson correlation (`stats.pearsonr`) between study minutes and daily completed actions
        """
        quiz_percentages = list(
            Quiz.objects.filter(completed=True)
            .order_by("created_at", "id")
            .values_list("percentage", flat=True)
        )
        scores = np.array(quiz_percentages, dtype=np.float64)

        if len(scores) >= 2 and np.std(scores) > 0:
            x_axis = np.arange(1, len(scores) + 1, dtype=np.float64)
            reg = stats.linregress(x_axis, scores)
            slope = float(np.round(reg.slope, 3))
            intercept = float(np.round(reg.intercept, 3))
            r_value = float(np.round(reg.rvalue, 3))
            p_value = float(np.round(reg.pvalue, 4))
            next_predicted = float(np.clip(np.round(reg.intercept + reg.slope * (len(scores) + 1), 1), 0.0, 100.0))
            z_scores = np.round(stats.zscore(scores), 2).tolist()
            mean_val = float(np.mean(scores))
            std_val = float(np.std(scores, ddof=1)) if len(scores) > 1 else 1.0
            prob_above_75 = float(np.round((1.0 - stats.norm.cdf(75.0, loc=mean_val, scale=max(std_val, 1.0))) * 100.0, 1))
            skewness = float(np.round(stats.skew(scores), 3)) if len(scores) >= 3 else 0.0
        elif len(scores) >= 1:
            slope = 0.0
            intercept = float(scores[0])
            r_value = 0.0
            p_value = 1.0
            next_predicted = float(np.round(np.mean(scores), 1))
            z_scores = [0.0 for _ in scores]
            prob_above_75 = 100.0 if np.mean(scores) >= 75.0 else 50.0
            skewness = 0.0
        else:
            slope = 0.0
            intercept = 0.0
            r_value = 0.0
            p_value = 1.0
            next_predicted = 0.0
            z_scores = []
            prob_above_75 = 0.0
            skewness = 0.0

        # Correlation between study minutes and completed actions in StudyLog
        logs = list(StudyLog.objects.order_by("date"))
        if len(logs) >= 2:
            mins_vec = np.array([l.study_minutes for l in logs], dtype=np.float64)
            actions_vec = np.array([l.total_actions for l in logs], dtype=np.float64)
            if np.std(mins_vec) > 0 and np.std(actions_vec) > 0:
                corr_r, corr_p = stats.pearsonr(mins_vec, actions_vec)
                study_correlation = float(np.round(corr_r, 3))
                study_corr_pvalue = float(np.round(corr_p, 4))
            else:
                study_correlation = 0.0
                study_corr_pvalue = 1.0
        else:
            study_correlation = 0.0
            study_corr_pvalue = 1.0

        if slope > 0.5:
            trend_label = "Upward Improvement Trend"
        elif slope < -0.5:
            trend_label = "Needs Revision Focus"
        else:
            trend_label = "Steady Performance"

        return {
            "regression_slope": slope,
            "regression_intercept": intercept,
            "correlation_r": r_value,
            "p_value": p_value,
            "predicted_next_score": next_predicted,
            "z_scores": z_scores,
            "probability_above_75_pct": prob_above_75,
            "score_skewness": skewness,
            "study_efficiency_correlation": study_correlation,
            "study_efficiency_pvalue": study_corr_pvalue,
            "trend_interpretation": trend_label,
        }

    # ==========================================================
    # PART 17: NETWORKX KNOWLEDGE MAP
    # ==========================================================
    @classmethod
    def build_knowledge_graph(cls) -> nx.DiGraph:
        """
        Build a NetworkX Directed Graph (`nx.DiGraph`) representing relationships between:
        Subjects -> Topics -> Notes.
        """
        graph = nx.DiGraph()
        root_id = "hub:Notes Manager"
        graph.add_node(
            root_id,
            label="Knowledge Hub",
            node_type="root",
            color=cls.COLOR_DARK_BURGUNDY,
            size=950,
        )

        subjects = Subject.objects.prefetch_related("notes").all()
        for subject in subjects:
            notes_in_subject = list(subject.notes.all())
            if not notes_in_subject and subject.is_custom is False and subject.name == "Other":
                continue

            subj_node_id = f"subject:{subject.name}"
            graph.add_node(
                subj_node_id,
                label=subject.name,
                node_type="subject",
                color=cls.COLOR_DARK_SECONDARY,
                size=700,
                total_notes=len(notes_in_subject),
            )
            graph.add_edge(root_id, subj_node_id, relation="contains_subject")

            for note in notes_in_subject:
                topic_label = (note.topic or "Core Concepts").strip()
                topic_node_id = f"topic:{subject.name}:{topic_label}"

                if not graph.has_node(topic_node_id):
                    graph.add_node(
                        topic_node_id,
                        label=topic_label,
                        subject=subject.name,
                        node_type="topic",
                        color=cls.COLOR_SECONDARY_ROSE,
                        size=460,
                    )
                    graph.add_edge(subj_node_id, topic_node_id, relation="has_topic")

                note_node_id = f"note:{note.id}"
                graph.add_node(
                    note_node_id,
                    label=note.title,
                    note_id=note.id,
                    subject=subject.name,
                    topic=topic_label,
                    covered=note.covered,
                    node_type="note",
                    color=cls.COLOR_PRIMARY_ROSE if note.covered else cls.COLOR_MUTED_ROSE,
                    size=320,
                )
                graph.add_edge(topic_node_id, note_node_id, relation="covers_note")

        return graph

    @classmethod
    def get_knowledge_map_data(cls) -> Dict[str, Any]:
        """
        Compute NetworkX layout coordinates, centrality scores, and hierarchical tree structure
        for the frontend Knowledge Map visualization.
        """
        graph = cls.build_knowledge_graph()
        undirected = graph.to_undirected()

        centrality = nx.degree_centrality(undirected) if len(undirected) > 1 else {}
        pos = nx.spring_layout(undirected, k=0.95, iterations=60, seed=42) if len(undirected) > 0 else {}

        nodes_payload: List[Dict[str, Any]] = []
        for node_id, attrs in graph.nodes(data=True):
            coord = pos.get(node_id, np.array([0.0, 0.0]))
            nodes_payload.append(
                {
                    "id": node_id,
                    "label": attrs.get("label", node_id),
                    "type": attrs.get("node_type", "note"),
                    "subject": attrs.get("subject", ""),
                    "topic": attrs.get("topic", ""),
                    "note_id": attrs.get("note_id"),
                    "covered": attrs.get("covered", True),
                    "color": attrs.get("color", cls.COLOR_PRIMARY_ROSE),
                    "centrality": round(float(centrality.get(node_id, 0.0)), 3),
                    "degree": int(graph.degree(node_id)),
                    "x": round(float(coord[0]), 4),
                    "y": round(float(coord[1]), 4),
                }
            )

        edges_payload = [
            {"source": u, "target": v, "relation": d.get("relation", "linked")}
            for u, v, d in graph.edges(data=True)
        ]

        # Build structured tree for clean hierarchy cards as well
        subject_trees: List[Dict[str, Any]] = []
        for subject in Subject.objects.prefetch_related("notes").all():
            notes_list = list(subject.notes.all())
            if not notes_list:
                continue
            topics_map: Dict[str, List[Dict[str, Any]]] = {}
            for n in notes_list:
                t_name = (n.topic or "Core Concepts").strip()
                topics_map.setdefault(t_name, []).append(
                    {
                        "id": n.id,
                        "title": n.title,
                        "covered": n.covered,
                        "reading_progress": n.reading_progress,
                    }
                )
            subject_trees.append(
                {
                    "subject": subject.name,
                    "total_notes": len(notes_list),
                    "covered_notes": sum(1 for n in notes_list if n.covered),
                    "topics": [
                        {"topic": t_key, "notes": t_notes}
                        for t_key, t_notes in topics_map.items()
                    ],
                }
            )

        top_hubs = sorted(
            [n for n in nodes_payload if n["type"] in ("subject", "topic")],
            key=lambda item: (item["centrality"], item["degree"]),
            reverse=True,
        )[:5]

        return {
            "total_nodes": graph.number_of_nodes(),
            "total_edges": graph.number_of_edges(),
            "density": round(float(nx.density(undirected)), 4) if len(undirected) > 1 else 0.0,
            "connected_components": nx.number_connected_components(undirected) if len(undirected) > 0 else 0,
            "top_hubs": top_hubs,
            "nodes": nodes_payload,
            "edges": edges_payload,
            "subject_trees": subject_trees,
        }

    # ==========================================================
    # PART 16: MATPLOTLIB STUDY ANALYTICS CHARTS
    # ==========================================================
    @classmethod
    def _fig_to_base64(cls, fig: Any) -> str:
        buffer = io.BytesIO()
        fig.savefig(buffer, format="png", dpi=130, bbox_inches="tight", facecolor=fig.get_facecolor())
        plt.close(fig)
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode("ascii")
        return f"data:image/png;base64,{encoded}"

    @classmethod
    def generate_quiz_trend_chart(cls) -> str:
        """Matplotlib chart 1: Quiz Score Over Time with SciPy Regression Trendline."""
        quizzes = list(Quiz.objects.filter(completed=True).order_by("created_at", "id")[:12])
        fig, ax = plt.subplots(figsize=(6.5, 3.4), facecolor=cls.COLOR_CARD_BG)
        ax.set_facecolor(cls.COLOR_SURFACE_CREAM)

        if quizzes:
            x = np.arange(1, len(quizzes) + 1)
            y = np.array([q.percentage for q in quizzes], dtype=np.float64)
            labels = [f"Q{i}" for i in x]

            ax.plot(
                x,
                y,
                marker="o",
                linewidth=2.5,
                markersize=7,
                color=cls.COLOR_DARK_BURGUNDY,
                label="Quiz Score (%)",
            )
            ax.fill_between(x, y, color=cls.COLOR_PRIMARY_ROSE, alpha=0.22)

            if len(x) >= 2 and np.std(y) > 0:
                reg = stats.linregress(x, y)
                trend_y = reg.intercept + reg.slope * x
                ax.plot(
                    x,
                    trend_y,
                    linestyle="--",
                    linewidth=1.8,
                    color=cls.COLOR_DARK_SECONDARY,
                    label=f"SciPy Trend (slope {reg.slope:+.1f})",
                )
            ax.set_xticks(x)
            ax.set_xticklabels(labels, color=cls.COLOR_TEXT_DARK, fontsize=9)
            ax.legend(loc="lower right", frameon=True, facecolor=cls.COLOR_CARD_BG, fontsize=8.5)
        else:
            ax.text(
                0.5,
                0.5,
                "Complete a Quiz to view score trends",
                ha="center",
                va="center",
                color=cls.COLOR_DARK_BURGUNDY,
                fontsize=11,
            )

        ax.set_ylim(0, 105)
        ax.set_title("Quiz Performance & SciPy Regression Trend", color=cls.COLOR_TEXT_DARK, fontsize=11, fontweight="bold", pad=10)
        ax.set_ylabel("Score (%)", color=cls.COLOR_TEXT_DARK, fontsize=9)
        ax.grid(True, linestyle=":", alpha=0.45, color=cls.COLOR_PRIMARY_ROSE)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color(cls.COLOR_SECONDARY_ROSE)
        return cls._fig_to_base64(fig)

    @classmethod
    def generate_notes_coverage_chart(cls) -> str:
        """Matplotlib chart 2: Covered vs Pending Notes across Subjects."""
        subjects = list(Subject.objects.prefetch_related("notes").all())
        names: List[str] = []
        covered_counts: List[int] = []
        pending_counts: List[int] = []

        for s in subjects:
            total = s.notes.count()
            if total == 0 and s.name == "Other":
                continue
            cov = s.notes.filter(covered=True).count()
            names.append(s.name[:16])
            covered_counts.append(cov)
            pending_counts.append(total - cov)

        fig, ax = plt.subplots(figsize=(6.5, 3.4), facecolor=cls.COLOR_CARD_BG)
        ax.set_facecolor(cls.COLOR_SURFACE_CREAM)

        if names:
            y_pos = np.arange(len(names))
            ax.barh(y_pos, covered_counts, color=cls.COLOR_DARK_BURGUNDY, height=0.55, label="Covered")
            ax.barh(
                y_pos,
                pending_counts,
                left=covered_counts,
                color=cls.COLOR_PRIMARY_ROSE,
                height=0.55,
                alpha=0.65,
                label="Pending",
            )
            ax.set_yticks(y_pos)
            ax.set_yticklabels(names, color=cls.COLOR_TEXT_DARK, fontsize=9)
            ax.invert_yaxis()
            ax.legend(loc="lower right", frameon=True, facecolor=cls.COLOR_CARD_BG, fontsize=8.5)
        else:
            ax.text(0.5, 0.5, "Add study notes to view coverage chart", ha="center", va="center", color=cls.COLOR_DARK_BURGUNDY)

        ax.set_title("Notes Coverage by Subject", color=cls.COLOR_TEXT_DARK, fontsize=11, fontweight="bold", pad=10)
        ax.set_xlabel("Number of Notes", color=cls.COLOR_TEXT_DARK, fontsize=9)
        ax.grid(True, axis="x", linestyle=":", alpha=0.45, color=cls.COLOR_PRIMARY_ROSE)
        for spine in ("top", "right"):
            ax.spines[spine].set_visible(False)
        for spine in ("left", "bottom"):
            ax.spines[spine].set_color(cls.COLOR_SECONDARY_ROSE)
        return cls._fig_to_base64(fig)

    @classmethod
    def generate_weekly_activity_chart(cls) -> str:
        """Matplotlib chart 3: Last 7 Days Study Minutes & Completed Actions."""
        today = timezone.localdate()
        days = [today - timedelta(days=i) for i in range(6, -1, -1)]
        logs_map = {log.date: log for log in StudyLog.objects.filter(date__gte=days[0])}

        labels = [d.strftime("%a\n%d") for d in days]
        minutes = [logs_map[d].study_minutes if d in logs_map else 0 for d in days]
        actions = [logs_map[d].total_actions if d in logs_map else 0 for d in days]

        fig, ax1 = plt.subplots(figsize=(6.5, 3.4), facecolor=cls.COLOR_CARD_BG)
        ax1.set_facecolor(cls.COLOR_SURFACE_CREAM)

        x = np.arange(len(days))
        ax1.bar(x, minutes, color=cls.COLOR_PRIMARY_ROSE, width=0.5, alpha=0.85, label="Study Minutes")
        ax1.set_xticks(x)
        ax1.set_xticklabels(labels, color=cls.COLOR_TEXT_DARK, fontsize=8.5)
        ax1.set_ylabel("Study Minutes", color=cls.COLOR_DARK_BURGUNDY, fontsize=9)

        ax2 = ax1.twinx()
        ax2.plot(x, actions, color=cls.COLOR_DARK_BURGUNDY, marker="s", linewidth=2.2, label="Study Actions")
        ax2.set_ylabel("Completed Actions", color=cls.COLOR_DARK_SECONDARY, fontsize=9)
        ax2.spines["top"].set_visible(False)

        ax1.set_title("Weekly Study Consistency & Activity", color=cls.COLOR_TEXT_DARK, fontsize=11, fontweight="bold", pad=10)
        ax1.grid(True, axis="y", linestyle=":", alpha=0.45, color=cls.COLOR_PRIMARY_ROSE)
        for spine in ("top", "right"):
            ax1.spines[spine].set_visible(False)
        return cls._fig_to_base64(fig)

    @classmethod
    def generate_networkx_chart(cls) -> str:
        """Matplotlib chart 4: Visual rendering of the NetworkX Knowledge Map."""
        graph = cls.build_knowledge_graph()
        undirected = graph.to_undirected()

        fig, ax = plt.subplots(figsize=(8.0, 4.6), facecolor=cls.COLOR_CARD_BG)
        ax.set_facecolor(cls.COLOR_SURFACE_CREAM)

        if len(undirected) > 0:
            pos = nx.spring_layout(undirected, k=0.95, iterations=65, seed=42)
            node_colors = [graph.nodes[n].get("color", cls.COLOR_PRIMARY_ROSE) for n in graph.nodes()]
            node_sizes = [graph.nodes[n].get("size", 350) for n in graph.nodes()]
            labels = {
                n: (
                    graph.nodes[n].get("label", n)[:20]
                    + (".." if len(graph.nodes[n].get("label", n)) > 20 else "")
                )
                for n in graph.nodes()
            }

            nx.draw_networkx_edges(
                graph,
                pos,
                ax=ax,
                edge_color=cls.COLOR_SECONDARY_ROSE,
                alpha=0.55,
                arrows=True,
                arrowsize=11,
                width=1.4,
            )
            nx.draw_networkx_nodes(
                graph,
                pos,
                ax=ax,
                node_color=node_colors,
                node_size=node_sizes,
                edgecolors=cls.COLOR_DARK_BURGUNDY,
                linewidths=1.2,
            )
            nx.draw_networkx_labels(
                graph,
                pos,
                labels=labels,
                ax=ax,
                font_size=7.5,
                font_color=cls.COLOR_TEXT_DARK,
                font_weight="bold",
            )
        ax.set_title("NetworkX Knowledge Map (Subjects → Topics → Notes)", color=cls.COLOR_TEXT_DARK, fontsize=11.5, fontweight="bold")
        ax.axis("off")
        return cls._fig_to_base64(fig)

    @classmethod
    def get_full_analytics_payload(cls, include_charts: bool = True) -> Dict[str, Any]:
        """Combine Progress, NumPy, SciPy, NetworkX, and Matplotlib charts into one payload."""
        progress_data = ProgressTracker.calculate_progress_metrics(update_today_log=False)
        numpy_data = cls.compute_numpy_metrics()
        scipy_data = cls.compute_scipy_statistics()
        knowledge_data = cls.get_knowledge_map_data()

        charts = {}
        if include_charts:
            charts = {
                "quiz_trend_chart": cls.generate_quiz_trend_chart(),
                "notes_coverage_chart": cls.generate_notes_coverage_chart(),
                "weekly_activity_chart": cls.generate_weekly_activity_chart(),
                "knowledge_map_chart": cls.generate_networkx_chart(),
            }

        return {
            "progress": progress_data,
            "numpy_analysis": numpy_data,
            "scipy_analysis": scipy_data,
            "knowledge_map": knowledge_data,
            "charts": charts,
        }
