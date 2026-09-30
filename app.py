import os, uuid
import pandas as pd
import streamlit as st
import plotly.express as px

from src.rag.retriever import build_default_kb, KnowledgeBase
from src.core.orchestrator import EvaluationOrchestrator
from src.core.models import EvaluationInput
from src.storage.database import EvaluationDB
from src.reporting.pdf_report import build_pdf

st.set_page_config(page_title='AI Response Validation Studio', page_icon='🧪', layout='wide', initial_sidebar_state='expanded')

st.markdown('''
<style>
:root{--ink:#101828;--muted:#667085;--teal:#0f766e;--cyan:#0891b2;--violet:#7c3aed;--line:#e4e7ec;--bg:#f7f9fc;}
.stApp{background:linear-gradient(180deg,#f8fafc 0%,#ffffff 55%,#f8fafc 100%);color:var(--ink)}
.block-container{padding-top:1.4rem;max-width:1500px}
.hero{background:radial-gradient(circle at 85% 20%,rgba(8,145,178,.30),transparent 32%),linear-gradient(135deg,#111827,#172554 58%,#0f766e);padding:28px 32px;border-radius:24px;color:white;box-shadow:0 20px 45px rgba(15,23,42,.15);margin-bottom:18px}
.hero h1{font-size:2.25rem;margin:0 0 6px;font-weight:800;letter-spacing:-.04em}.hero p{margin:0;color:#dbeafe}
.card{background:white;border:1px solid var(--line);border-radius:18px;padding:18px 20px;box-shadow:0 8px 24px rgba(16,24,40,.05)}
.metric{background:white;border:1px solid var(--line);border-radius:18px;padding:16px 18px}.metric .label{font-size:.82rem;color:var(--muted)}.metric .value{font-size:1.85rem;font-weight:800;margin-top:4px}
.badge{display:inline-block;padding:5px 10px;border-radius:999px;font-size:.78rem;font-weight:700}.pass{background:#dcfce7;color:#166534}.needs{background:#fef3c7;color:#92400e}.fail{background:#fee2e2;color:#991b1b}
.small{font-size:.85rem;color:var(--muted)}
section[data-testid="stSidebar"]{background:#0b1220}section[data-testid="stSidebar"] *{color:#e5e7eb!important}
.stButton>button{border-radius:12px;font-weight:700}
</style>
''', unsafe_allow_html=True)

@st.cache_resource
def get_kb(): return build_default_kb('data/reference_knowledge.csv')
@st.cache_resource
def get_db(): return EvaluationDB('data/evaluations.db')

def badge(v):
    cls='pass' if v=='Pass' else 'needs' if v=='Needs Improvement' else 'fail'
    return f'<span class="badge {cls}">{v}</span>'

def result_frame(results):
    rows=[]
    for r in results:
        rows.append({'ID':r['record_id'],'Question':r['question'][:90],'Relevance':r['relevance']['score'],'Accuracy':r['accuracy']['score'],'Hallucination Safety':r['hallucination']['score'],'Completeness':r['completeness']['score'],'Overall':round(r['overall_score'],2),'Verdict':r['verdict']})
    return pd.DataFrame(rows)

def display_result(r):
    c1,c2,c3,c4,c5=st.columns(5)
    for c,label,key in [(c1,'Relevance','relevance'),(c2,'Accuracy','accuracy'),(c3,'Hallucination Safety','hallucination'),(c4,'Completeness','completeness')]:
        c.metric(label,f"{r[key]['score']}/5")
    c5.metric('Overall',f"{r['overall_score']:.2f}/5")
    st.markdown(f"### Verdict {badge(r['verdict'])}",unsafe_allow_html=True)
    st.info(r['consolidated_reasoning'])
    tabs=st.tabs(['Relevance','Accuracy & Evidence','Hallucination Flags','Completeness'])
    for tab,key in zip(tabs,['relevance','accuracy','hallucination','completeness']):
        with tab:
            a=r[key]
            st.write(a['reasoning'])
            if a.get('evidence'):
                st.markdown('**Supporting evidence**')
                for e in a['evidence']: st.caption(f"{e['source_id']} · similarity {e['score']:.2f}\n\n{e['text']}")
            if a.get('issues'):
                st.markdown('**Issues / missing aspects**')
                for x in a['issues']: st.write('• '+x)
            if a.get('flags'):
                st.markdown('**Flagged claims**')
                for x in a['flags']: st.error(x)

st.markdown('<div class="hero"><h1>🧪 AI Response Validation Studio</h1><p>Milestones 1–4 · RAG-grounded evaluation · agent scoring · batch analytics · professional reporting</p></div>',unsafe_allow_html=True)

with st.sidebar:
    st.markdown('## Control Center')
    page=st.radio('Workspace',['Single Evaluation','Batch Evaluation','Executive Dashboard','Knowledge Base','Documentation'])
    st.markdown('---')
    st.caption('Evaluation dimensions')
    st.write('• Relevance 25%\n• Accuracy 30%\n• Hallucination Safety 25%\n• Completeness 20%')
    st.caption('Verdict rules')
    st.write('Pass ≥ 4.0 · Needs Improvement 2.8–3.99 · Fail < 2.8 or critical failure')

kb=get_kb(); db=get_db(); orch=EvaluationOrchestrator(kb)

if page=='Single Evaluation':
    st.subheader('Single-response evaluation')
    st.caption('Submit a question and AI response. A reference answer is optional; the local RAG knowledge base supplies evidence when available.')
    with st.form('single'):
        q=st.text_area('Question',placeholder='e.g. What is the capital of France?')
        resp=st.text_area('AI Generated Response',height=160,placeholder='Paste the model response here...')
        ref=st.text_area('Reference Answer (optional)',height=120)
        source_file=st.file_uploader('Source Document (optional)',type=['txt','md','csv'])
        submitted=st.form_submit_button('Evaluate Response',use_container_width=True,type='primary')
    if submitted:
        if not q.strip() or not resp.strip(): st.error('Please enter both a question and an AI response.')
        else:
            with st.spinner('Running relevance, accuracy, hallucination, completeness and verdict agents...'):
                source_text=''
                if source_file is not None:
                    source_text=source_file.getvalue().decode('utf-8', errors='ignore')
                result=orch.evaluate(EvaluationInput(q,resp,ref,source_text=source_text))
                db.save(result)
            st.success('Evaluation completed and stored.')
            display_result(result.to_dict())

elif page=='Batch Evaluation':
    st.subheader('Batch evaluation workspace')
    st.caption('CSV columns: question, ai_response, optional reference_answer, source_info, record_id')
    uploaded=st.file_uploader('Upload CSV',type=['csv'])
    if uploaded:
        df=pd.read_csv(uploaded)
        required={'question','ai_response'}
        missing=required-set(df.columns)
        if missing: st.error(f'Missing required columns: {sorted(missing)}')
        else:
            st.dataframe(df.head(10),use_container_width=True)
            if st.button('Run Batch Evaluation',type='primary',use_container_width=True):
                batch_id='batch-'+uuid.uuid4().hex[:8]
                results=[]; invalid=[]; progress=st.progress(0)
                for i,row in df.iterrows():
                    q=str(row.get('question','')).strip(); resp=str(row.get('ai_response','')).strip()
                    if not q or not resp: invalid.append(i+1); continue
                    try:
                        r=orch.evaluate(EvaluationInput(q,resp,str(row.get('reference_answer','') or '')),batch_id=batch_id)
                        db.save(r); results.append(r.to_dict())
                    except Exception as e: invalid.append(f'{i+1}: {e}')
                    progress.progress((i+1)/len(df))
                st.session_state['last_batch']=results
                st.session_state['last_batch_id']=batch_id
                if invalid: st.warning(f'{len(invalid)} record(s) were skipped/failed: {invalid[:8]}')
                st.success(f'Completed {len(results)} of {len(df)} records.')
    results=st.session_state.get('last_batch',[])
    if results:
        frame=result_frame(results); st.dataframe(frame,use_container_width=True,hide_index=True)
        pdf=build_pdf(results,title=f"AI Response Validation — {st.session_state.get('last_batch_id','Batch')}")
        st.download_button('Download Batch PDF Report',pdf,file_name='ai_response_validation_report.pdf',mime='application/pdf',use_container_width=True)
        selected=st.selectbox('Inspect record',frame['ID'].tolist())
        display_result(next(r for r in results if r['record_id']==selected))

elif page=='Executive Dashboard':
    st.subheader('Executive quality dashboard')
    allr=db.all()
    if not allr:
        st.info('No stored evaluations yet. Run a single or batch evaluation first.')
    else:
        frame=result_frame(allr)
        verdict_filter=st.multiselect('Verdict filter',['Pass','Needs Improvement','Fail'],default=['Pass','Needs Improvement','Fail'])
        view=frame[frame['Verdict'].isin(verdict_filter)]
        a,b,c,d=st.columns(4)
        a.markdown(f'<div class="metric"><div class="label">Responses evaluated</div><div class="value">{len(view)}</div></div>',unsafe_allow_html=True)
        a=a
        b.markdown(f'<div class="metric"><div class="label">Pass rate</div><div class="value">{(view.Verdict.eq("Pass").mean()*100 if len(view) else 0):.0f}%</div></div>',unsafe_allow_html=True)
        c.markdown(f'<div class="metric"><div class="label">Average score</div><div class="value">{(view.Overall.mean() if len(view) else 0):.2f}</div></div>',unsafe_allow_html=True)
        d.markdown(f'<div class="metric"><div class="label">Hallucination alerts</div><div class="value">{sum(len(r["hallucination"]["flags"])>0 for r in allr)}</div></div>',unsafe_allow_html=True)
        st.markdown('### Quality profile')
        dims=['Relevance','Accuracy','Hallucination Safety','Completeness']
        vals=[view[x].mean() for x in dims]
        fig=px.bar(x=dims,y=vals,range_y=[0,5],labels={'x':'Dimension','y':'Average score'},title='Average dimension score')
        st.plotly_chart(fig,use_container_width=True)
        left,right=st.columns(2)
        with left:
            vc=view['Verdict'].value_counts().rename_axis('Verdict').reset_index(name='Count')
            st.plotly_chart(px.pie(vc,names='Verdict',values='Count',hole=.55,title='Verdict distribution'),use_container_width=True)
        with right:
            long=view.melt(id_vars=['ID'],value_vars=dims,var_name='Dimension',value_name='Score')
            st.plotly_chart(px.box(long,x='Dimension',y='Score',points='all',range_y=[0,5],title='Score distribution'),use_container_width=True)
        st.markdown('### Evaluation records')
        st.dataframe(view.sort_values('Overall'),use_container_width=True,hide_index=True)

elif page=='Knowledge Base':
    st.subheader('Reference Knowledge Base')
    st.caption('Milestone 1 RAG layer. The included implementation is local/offline and uses TF-IDF semantic retrieval.')
    st.dataframe(pd.DataFrame(kb.records),use_container_width=True)
    txt=st.text_area('Add a reference document/chunk')
    if st.button('Index document') and txt.strip():
        kb.add_text('user-doc-'+uuid.uuid4().hex[:6],txt); st.cache_resource.clear(); st.success('Indexed into the active knowledge base for this session.')

else:
    st.subheader('Documentation & architecture')
    st.markdown('''
### Milestone coverage
- **M1:** input UI, knowledge base, chunking, TF-IDF embeddings, retrieval, storage, architecture.
- **M2:** relevance, accuracy, hallucination agents + consistency tests.
- **M3:** completeness, weighted verdict, per-dimension UI, batch evaluation.
- **M4:** dashboard, PDF export, end-to-end tests, technical docs, demo guide.

### Professional dashboard design
The dashboard is designed as an evaluation workspace rather than a generic admin page: an executive metric row, quality profile, verdict distribution, score distribution, drill-down records, and evidence-first detail panels.

### Production upgrade path
1. Replace TF-IDF with sentence-transformer embeddings + FAISS/Chroma.
2. Replace deterministic judge internals with structured LLM-as-a-Judge prompts.
3. Add authentication and user/workspace isolation.
4. Calibrate thresholds against a human-labeled validation set.
5. Add source-level claim entailment and citation verification.
''')
