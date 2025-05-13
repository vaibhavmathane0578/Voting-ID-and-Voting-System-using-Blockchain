document.addEventListener('DOMContentLoaded', () => {
  const rows = document.querySelectorAll('.candidate-row');
  const hiddenInput = document.getElementById('selected_proposal');
  const submitBtn = document.getElementById('submit-vote-btn');
  const messageArea = document.getElementById('confirmation-message');

  rows.forEach(row => {
    const btn = row.querySelector('.vote-button');
    const light = row.querySelector('.indicator-light');

    btn.addEventListener('click', () => {
      // clear previous selection
      rows.forEach(r => {
        r.classList.remove('selected-for-vote');
        r.querySelector('.indicator-light').classList.remove('active');
        r.querySelector('.vote-button').disabled = false;
      });
      // mark this one
      row.classList.add('selected-for-vote');
      light.classList.add('active');
      btn.disabled = true;

      // store value & enable submit
      hiddenInput.value = row.dataset.id;
      submitBtn.disabled = false;

      // show confirmation
      messageArea.textContent = `You selected "${row.dataset.proposalName}". Now enter your details.`;
      messageArea.classList.add('selected');
      messageArea.classList.remove('error');
    });
  });

  // optional: validate address format
  const addressField = document.getElementById('address');
  addressField.addEventListener('input', () => {
    const re = /^0x[a-fA-F0-9]{40}$/;
    if (!re.test(addressField.value)) {
      messageArea.textContent = 'Invalid Ethereum address format.';
      messageArea.classList.add('error');
      submitBtn.disabled = true;
    } else if (hiddenInput.value) {
      messageArea.textContent = 'Ready to submit!';
      messageArea.classList.remove('error');
      messageArea.classList.add('selected');
      submitBtn.disabled = false;
    }
  });
});
