# app.py

from flask import Flask, render_template, request, redirect, url_for, flash
from web3 import Web3, HTTPProvider
import json, qrcode, io, base64
from datetime import datetime, date

app = Flask(__name__)
app.config['SECRET_KEY'] = 'replace-with-a-secure-key'

# --- Web3 / Contract setup ---
RPC_URL = "http://127.0.0.1:8545"
w3 = Web3(HTTPProvider(RPC_URL))
accounts = w3.eth.accounts if hasattr(w3.eth, 'accounts') else w3.eth.get_accounts()
w3.eth.default_account = accounts[0]

def load_abi(path):
    with open(path) as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and 'abi' in data:
            return data['abi']
        raise ValueError(f"Unrecognized ABI format in {path}")

voting_id_abi = load_abi("DocumentContract_abi.json")
voting_abi    = load_abi("VotingContract_abi.json")

VOTING_ID_ADDR = "0x7E29e1386d75b96EBc999D3c2b2bA12d83dd2155"
VOTING_ADDR    = "0x77930034e047cCd0fBFB1e8e0c774d219d1BE57D"

voting_id = w3.eth.contract(address=VOTING_ID_ADDR, abi=voting_id_abi)
voting    = w3.eth.contract(address=VOTING_ADDR,    abi=voting_abi)

def calculate_age(dob_str):
    dob = datetime.strptime(dob_str, "%Y-%m-%d").date()
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/issue", methods=["GET", "POST"])
def issue():
    if request.method == "POST":
        name       = request.form.get("name")
        dob        = request.form.get("dob")
        voterId    = request.form.get("voterId")
        wallet     = request.form.get("wallet")
        privateKey = request.form.get("private_key")

        if calculate_age(dob) < 18:
            flash("You must be at least 18 years old.", "error")
            return redirect(url_for("issue"))

        try:
            nonce = w3.eth.get_transaction_count(wallet)
            tx = voting_id.functions.issueID(name, dob, voterId).build_transaction({
                'from': wallet,
                'nonce': nonce,
                'gas': 3000000,
                'gasPrice': w3.to_wei('10', 'gwei')
            })
            signed = w3.eth.account.sign_transaction(tx, private_key=privateKey)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash)

        except Exception as e:
            flash(f"Error issuing ID: {e}", "error")
            return redirect(url_for("issue"))

        verify_url = url_for('verify_qr', voterId=voterId, _external=True)
        img = qrcode.make(verify_url)
        # Save QR in static folder
        qr_filename = f"static/{voterId}.png"
        img.save(qr_filename)

        # Prepare for displaying in HTML
        with open(qr_filename, "rb") as f:
            qr_data = base64.b64encode(f.read()).decode()   

        flash("Voter ID issued successfully!", "success")
        return render_template("issue.html", issued=True, qr_data=qr_data, voterId=voterId)

    return render_template("issue.html", issued=False)

@app.route("/verify/<voterId>")
def verify_qr(voterId):
    try:
        name, dob, voter_id, isValid = voting_id.functions.getIDByVoterId(voterId).call()
        return render_template("verify_result.html", name=name, dob=dob, voterId=voter_id, isValid=isValid)
    except Exception:
        flash("Invalid or unknown Voter ID.", "error")
        return redirect(url_for("home"))


@app.route("/verify", methods=["GET", "POST"])
def verify():
    if request.method == "POST":
        voterId = request.form.get("voterId")
        wallet  = request.form.get("wallet")
        

        if voterId:
            return redirect(url_for("verify_qr", voterId=voterId))
        elif wallet:
            try:
                name, dob, voter_id, isValid = voting_id.functions.getIDByAddress(wallet).call()
                if not isValid:
                    flash("Your ID has been revoked.", "error")
                    return redirect(url_for("verify"))
                return render_template("verify_result.html", name=name, dob=dob, voterId=voter_id, isValid=True)
            except:
                flash("No ID found for this wallet address.", "error")
        else:
            flash("Please enter either Voter ID or Wallet address.", "error")

    return render_template("verify.html")




@app.route("/vote", methods=["GET", "POST"])
def vote():
    if request.method == "POST":
        voterId = request.form.get("voterId")
        try:
            _, _, _, isValid = voting_id.functions.getIDByVoterId(voterId).call()
            if not isValid:
                flash("Your ID has been revoked.", "error")
                return redirect(url_for("home"))
        except Exception:
            flash("No such Voter ID found.", "error")
            return redirect(url_for("home"))

        proposals = []
        count = voting.functions.getProposalCount().call()
        for i in range(count):
            name, count_votes = voting.functions.getProposal(i).call()
            proposals.append({'index': i, 'name': name, 'count': count_votes})

        return render_template("vote.html", voterId=voterId, proposals=proposals)

    return render_template("verify_vote.html")

@app.route("/results")
def results():
    proposals = []
    count = voting.functions.getProposalCount().call()
    for i in range(count):
        name, count_votes = voting.functions.getProposal(i).call()
        proposals.append({'name': name, 'count': count_votes})
    return render_template("results.html", proposals=proposals)



@app.route("/submit-vote", methods=["POST"])
def submit_vote():
    voterId     = request.form.get("voterId")
    proposal_id = int(request.form.get("proposal"))
    wallet      = request.form.get("address")
    privateKey  = request.form.get("private_key")

    try:
        nonce = w3.eth.get_transaction_count(wallet)
        tx = voting.functions.vote(proposal_id, voterId).build_transaction({
            'from': wallet,
            'nonce': nonce,
            'gas': 3000000,
            'gasPrice': w3.to_wei('10', 'gwei')
        })
        signed = w3.eth.account.sign_transaction(tx, private_key=privateKey)
        tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
        w3.eth.wait_for_transaction_receipt(tx_hash)
        flash("Vote cast successfully!", "success")

    except Exception as e:
        flash(f"Error casting vote: {e}", "error")

    return redirect(url_for("results"))

if __name__ == "__main__":
    app.run(debug=True)
