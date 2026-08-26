from flask import render_template, request, redirect, url_for, session
from services.progress import record, stats
from services.database import connection
from services.groq_ai import ai

def register_v7(app):
    @app.route('/focus', methods=['GET','POST'])
    def focus():
        if not session.get('user_id'): return redirect(url_for('login', next=request.path))
        if request.method == 'POST':
            try: minutes=max(1,min(240,int(request.form.get('minutes','25'))))
            except ValueError: minutes=25
            record(session['user_id'],'focus',minutes//5+5)
            return redirect(url_for('focus', completed=minutes))
        return render_template('focus.html', completed=request.args.get('completed'))

    @app.route('/analytics')
    def analytics():
        if not session.get('user_id'): return redirect(url_for('login', next=request.path))
        uid=session['user_id']
        with connection() as conn:
            kinds=conn.execute("SELECT kind,COUNT(*) AS count,COALESCE(SUM(xp),0) AS xp FROM activity WHERE user_id=%s GROUP BY kind ORDER BY xp DESC",(uid,)).fetchall()
        return render_template('analytics.html', stats=stats(uid), kinds=kinds)

    @app.route('/achievements')
    def achievements():
        if not session.get('user_id'): return redirect(url_for('login', next=request.path))
        s=stats(session['user_id'])
        items=[('🌱','First Steps','Earn 10 XP',s['xp']>=10),('🏆','100 XP','Reach 100 XP',s['xp']>=100),('🎯','Quiz Runner','Complete 5 quizzes',s['quizzes']>=5),('🔥','Streak','Build a 7-day streak',s['streak']>=7),('💯','Perfect','Reach 100% quiz accuracy',s['accuracy']==100 and s['quizzes']>0)]
        return render_template('achievements.html', achievements=items)

    @app.route('/worksheet', methods=['GET','POST'])
    def worksheet():
        if not session.get('user_id'): return redirect(url_for('login', next=request.path))
        form={'grade':request.form.get('grade','7'),'subject':request.form.get('subject','Science'),'topic':request.form.get('topic',''),'count':request.form.get('count','10')}
        text=None
        if request.method=='POST':
            text=ai.ask(f"Create a Grade {form['grade']} {form['subject']} worksheet about {form['topic']} with exactly {form['count']} questions. Mix MCQ, short answer and application questions. Do not include answers. Format clearly for printing.","You are an expert school worksheet designer.")
        return render_template('worksheet.html',form=form,worksheet=text)
