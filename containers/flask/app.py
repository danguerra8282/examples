from flask import Flask
app = Flask(__name__)


@app.route('/')
def main():
    return '<h1>This is the beginning</h1>'


if __name__ == "__main__":
    app.run(debug=True)
