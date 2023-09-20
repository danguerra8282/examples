from flask import Flask, render_template
app = Flask(__name__)


@app.route('/')
def home():
    # return '<h1>This is the beginning</h1>'
    return render_template('home.html')


@app.route('/about/')
def about():
    return render_template('about.html')


if __name__ == "__main__":
    app.run(debug=True)
