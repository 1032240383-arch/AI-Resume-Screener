import os
import json
import requests
import threading
from pypdf import PdfReader
import tkinter as tk
from tkinter import ttk, messagebox

# --- CONFIGURATION ---
FOLDER_PATH = r"C:\Resume-Screener\Resume"
LM_STUDIO_URL = "http://localhost:1234/v1/chat/completions"

if not os.path.exists(FOLDER_PATH):
    os.makedirs(FOLDER_PATH)

def extract_pdf_text(filepath):
    try:
        reader = PdfReader(filepath)
        return "".join([page.extract_text() or "" for page in reader.pages])
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return ""

def parse_ai_json(raw_output):
    cleaned = raw_output.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    return json.loads(cleaned.strip())

class ModernResumeScreenerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Resume Screener & Project Auditor")
        self.root.geometry("1250x780")
        self.root.minsize(1000, 600)
        self.results_data = []

        self.apply_modern_styles()
        self.setup_ui()

    def apply_modern_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Treeview", font=("Segoe UI", 10), rowheight=32, background="#ffffff", fieldbackground="#ffffff")
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), background="#e2e8f0", foreground="#1e293b")
        style.map("Treeview", background=[("selected", "#3b82f6")], foreground=[("selected", "white")])

        style.configure("TLabelframe", font=("Segoe UI", 11, "bold"), foreground="#0f172a")
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)

    def setup_ui(self):
        # Header Banner
        header_frame = tk.Frame(self.root, bg="#1e293b", pady=12, padx=20)
        header_frame.pack(fill="x")
        tk.Label(header_frame, text="🛡️ Local AI Resume Auditor & Screener", font=("Segoe UI", 16, "bold"), fg="white", bg="#1e293b").pack(side="left")
        tk.Label(header_frame, text="Powered by LM Studio", font=("Segoe UI", 11), fg="#94a3b8", bg="#1e293b").pack(side="right")

        main_pane = tk.PanedWindow(self.root, orient="vertical", sashrelief="flat", sashwidth=6, bg="#cbd5e1")
        main_pane.pack(fill="both", expand=True, padx=15, pady=10)

        # TOP SECTION
        top_box = ttk.LabelFrame(main_pane, text=" Step 1: Target Job Requirements & Must-Have Projects ", padding=12)
        prompt_subframe = tk.Frame(top_box)
        prompt_subframe.pack(fill="x", expand=True)
        
        self.prompt_text = tk.Text(prompt_subframe, height=3, font=("Segoe UI", 10), wrap="word", relief="solid", bd=1)
        # Left completely blank as requested
        self.prompt_text.pack(side="left", fill="x", expand=True, padx=(0, 10))

        self.run_btn = tk.Button(prompt_subframe, text="🚀 SCAN RESUMES\n(Run Local GPU)", font=("Segoe UI", 11, "bold"), bg="#2563eb", fg="white", activebackground="#1d4ed8", activeforeground="white", relief="flat", cursor="hand2", padx=15, command=self.start_screening_thread)
        self.run_btn.pack(side="right", fill="y")

        main_pane.add(top_box)

        # BOTTOM SECTION
        split_body = tk.PanedWindow(main_pane, orient="horizontal", sashrelief="flat", sashwidth=6, bg="#cbd5e1")

        table_box = ttk.LabelFrame(split_body, text=" Step 2: Candidate Rankings ", padding=10)
        columns = ("score", "name", "project_found", "verdict")
        self.tree = ttk.Treeview(table_box, columns=columns, show="headings")
        self.tree.heading("score", text="Score")
        self.tree.heading("name", text="Candidate Name")
        self.tree.heading("project_found", text="Target Criteria Met?")
        self.tree.heading("verdict", text="Verdict")

        self.tree.column("score", width=70, anchor="center")
        self.tree.column("name", width=220, anchor="w")
        self.tree.column("project_found", width=140, anchor="center")
        self.tree.column("verdict", width=100, anchor="center")

        self.tree.tag_configure("shortlist", background="#dcfce7", foreground="#166534")
        self.tree.tag_configure("reject", background="#fee2e2", foreground="#991b1b")

        scrollbar = ttk.Scrollbar(table_box, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.tree.pack(fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self.on_row_select)

        split_body.add(table_box, width=580)

        inspect_box = ttk.LabelFrame(split_body, text=" Step 3: Detailed AI Audit Report & Score Justification ", padding=12)
        self.details_text = tk.Text(inspect_box, wrap="word", font=("Segoe UI", 10), state="disabled", bg="#f8fafc", relief="flat")
        self.details_text.pack(fill="both", expand=True)

        split_body.add(inspect_box, width=640)
        main_pane.add(split_body)

    def start_screening_thread(self):
        job_criteria = self.prompt_text.get("1.0", "end-1c").strip()
        if not job_criteria:
            messagebox.showwarning("Warning", "Please enter target job criteria!")
            return

        # Clear UI table and memory
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.results_data.clear()
        
        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.config(state="disabled")

        pdf_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith(".pdf")]
        if not pdf_files:
            messagebox.showwarning("Empty Folder", f"No PDF files found inside:\n{FOLDER_PATH}")
            return

        # Lock UI button and start background thread
        self.run_btn.config(state="disabled", bg="#94a3b8")
        threading.Thread(target=self._process_resumes_background, args=(job_criteria, pdf_files), daemon=True).start()

    def _process_resumes_background(self, job_criteria, pdf_files):
        total_files = len(pdf_files)
        
        for index, file in enumerate(pdf_files):
            # Safely update button text from background thread
            current_num = index + 1
            self.root.after(0, lambda n=current_num, t=total_files: self.run_btn.config(text=f"⏳ SCANNING ({n}/{t})"))

            filepath = os.path.join(FOLDER_PATH, file)
            text = extract_pdf_text(filepath).strip()

            if len(text) < 50:
                self.results_data.append({
                    "name": f"⚠️ Unreadable PDF ({file})",
                    "score": 0,
                    "step_by_step_analysis": "File text unreadable by script.",
                    "score_justification": "Score is 0 because the file contains no machine-readable text.",
                    "project_detected": "No",
                    "project_evidence": "ERROR: Could not extract text.",
                    "pros": "None",
                    "cons": "Unreadable file.",
                    "verdict": "Reject"
                })
                continue

            audit_prompt = f"""
            You are a sharp, objective technical auditor screening a resume against this requirement:
            "{job_criteria}"

            CRITICAL AUDITING RULES:
            1. Analyze the text step-by-step BEFORE deciding Yes or No.
            2. ALLOW SEMANTIC SYNONYMS AND TECH TERMS: Recognize that terms like "programming", "software development", "scripting", or explicitly listing core languages are exact functional matches for a requirement of "coding". Do not reject a candidate simply because they used a technical synonym.
            3. REJECT UNRELATED DOMAINS: Strictly reject candidates whose background is completely unrelated to the criteria.
            4. If the requirement is completely absent, set "project_detected" to "No".

            Output ONLY valid JSON matching this exact structure:
            {{
                "name": "Candidate Full Name extracted from resume",
                "step_by_step_analysis": "Identify the candidate's field of study or core technical focus. Trace the specific tools, languages, or projects they mentioned that successfully map to the target criteria.",
                "project_detected": "Yes" or "No",
                "project_evidence": "Copy-paste the exact verbatim sentence from the resume containing the relevant technical skills, languages, or projects.",
                "score": integer from 0 to 100 (Scale matching actual capability),
                "score_justification": "Explain the score layout clearly.",
                "pros": "Actual skills found",
                "cons": "Actual missing elements from the core job criteria",
                "verdict": "Shortlist" or "Reject"
            }}

            Resume Text to Audit:
            {text}
            """

            try:
                response = requests.post(
                    LM_STUDIO_URL,
                    json={
                        "model": "llama-3.1-8b-instruct",
                        "messages": [
                            {"role": "system", "content": "You are a factual, strict extraction AI. Output raw JSON only. Never invent facts."},
                            {"role": "user", "content": audit_prompt}
                        ],
                        "temperature": 0.0
                    },
                    timeout=90
                )
                
                raw_json = response.json()["choices"][0]["message"]["content"]
                data = parse_ai_json(raw_json)
                self.results_data.append(data)

            except requests.exceptions.ConnectionError:
                self.root.after(0, lambda: messagebox.showerror("Server Offline", "Could not connect to LM Studio!\n\nEnsure LM Studio is open and your server is running on port 1234."))
                self.root.after(0, self._restore_ui_after_processing)
                return
            except Exception as e:
                print(f"Error parsing AI output for {file}: {e}")
                self.results_data.append({
                    "name": f"⚠️ Parse Error ({file})",
                    "score": 0,
                    "step_by_step_analysis": "Failed to parse AI output into valid JSON.",
                    "score_justification": "N/A - Parsing failed.",
                    "project_detected": "No",
                    "project_evidence": "JSON format error.",
                    "pros": "N/A",
                    "cons": "Output formatting issue.",
                    "verdict": "Reject"
                })

        self.results_data.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        # Safely tell the GUI to update with the sorted results
        self.root.after(0, self._update_gui_with_results)

    def _update_gui_with_results(self):
        for item in self.results_data:
            verdict = item.get("verdict", "Reject")
            tag = "shortlist" if "shortlist" in str(verdict).lower() else "reject"
            
            self.tree.insert("", "end", values=(
                f"{item.get('score', 0)} / 100",
                item.get("name", "Unknown Candidate"),
                item.get("project_detected", "No"),
                verdict.upper()
            ), tags=(tag,))

        self._restore_ui_after_processing()
        messagebox.showinfo("Audit Complete", f"Successfully audited {len(self.results_data)} resumes!")

    def _restore_ui_after_processing(self):
        # Re-enable the scan button
        self.run_btn.config(state="normal", text="🚀 SCAN RESUMES\n(Run Local GPU)", bg="#2563eb")

    def on_row_select(self, event):
        selected_items = self.tree.selection()
        if not selected_items:
            return

        item_index = self.tree.index(selected_items[0])
        c = self.results_data[item_index]

        display_text = f"👤 CANDIDATE AUDIT REPORT: {str(c.get('name', 'Unknown')).upper()}\n"
        display_text += "━" * 55 + "\n\n"
        
        display_text += f"🏆 OVERALL MATCH SCORE  : {c.get('score', 0)} / 100\n"
        display_text += f"🎯 TARGET CRITERIA MET  : {c.get('project_detected', 'No')}\n"
        display_text += f"📋 FINAL RECOMMENDATION : {str(c.get('verdict', 'Review')).upper()}\n\n"
        
        display_text += "💡 WHY THIS SCORE? (SCORE JUSTIFICATION)\n"
        display_text += f"{c.get('score_justification', 'No explanation provided.')}\n\n"

        display_text += "🧠 STEP-BY-STEP AI ANALYSIS\n"
        display_text += f"{c.get('step_by_step_analysis', 'No analysis provided.')}\n\n"

        display_text += "🔎 VERBATIM TEXT EVIDENCE\n"
        display_text += f'"{c.get("project_evidence", "N/A")}"\n\n'

        display_text += f"✅ Identified Strengths : {c.get('pros', 'None listed')}\n"
        display_text += f"❌ Missing Requirements : {c.get('cons', 'None listed')}\n"

        self.details_text.config(state="normal")
        self.details_text.delete("1.0", "end")
        self.details_text.insert("1.0", display_text)
        self.details_text.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    app = ModernResumeScreenerApp(root)
    root.mainloop()