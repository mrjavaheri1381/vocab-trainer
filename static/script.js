const input = document.getElementById('user-input');
const result = document.getElementById('result');
const ratingButtons = document.getElementById('rating-buttons');
const showBtn = document.getElementById('show-btn');

let correctWord = "{{ word.word }}";

input.addEventListener("input", () => {
  if (input.value.toLowerCase().trim() === correctWord.toLowerCase()) {
    result.textContent = "✅ Correct!";
    ratingButtons.classList.remove("hidden");
  } else {
    result.textContent = "❌ Incorrect";
    ratingButtons.classList.add("hidden");
  }
});

function submitRating(score) {
  fetch(`/submit/${correctWord}/${score}`, { method: 'POST' })
    .then(() => window.location.reload());
}

showBtn.onclick = () => {
  alert("The word is: " + correctWord);
};

document.addEventListener("keydown", (e) => {
  if (e.key >= "0" && e.key <= "4") {
    submitRating(parseInt(e.key));
  } else if (e.key.toLowerCase() === "s") {
    submitRating(-1);
  }
});
