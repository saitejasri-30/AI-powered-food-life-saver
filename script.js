document.addEventListener("DOMContentLoaded", () => {
    const foodForm = document.getElementById("foodForm");
    const foodList = document.getElementById("foodList");
    const receiptUpload = document.getElementById("receiptUpload");
    const receiptStatus = document.getElementById("receiptStatus");
    const recipeSelect = document.getElementById("recipeIngredients");
    const recipeResult = document.getElementById("recipeResult");
  
    // 1) Load existing items from backend
    fetch("/items")
      .then(res => res.json())
      .then(items => {
        items.forEach(addRow);
      });
  
    // 2) Add a new food item
    foodForm.addEventListener("submit", e => {
      e.preventDefault();
      const name = foodForm.foodItem.value.trim();
      const purchase_date = foodForm.purchaseDate.value;
      if (!name || !purchase_date) return;
  
      fetch("/add", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, type: "food", purchase_date })
      })
      .then(res => res.json())
      .then(data => {
        addRow({ name, purchase_date, expiry_date: data.expiry_date });
        foodForm.reset();
      });
    });
  
    // 3) Upload receipt for OCR
    window.processReceipt = () => {
      if (!receiptUpload.files.length) {
        receiptStatus.textContent = "⚠ Please upload a receipt image!";
        return;
      }
      const form = new FormData();
      form.append("receipt", receiptUpload.files[0]);
      fetch("/receipt", { method: "POST", body: form })
        .then(res => res.json())
        .then(({ extracted_text }) => {
          receiptStatus.textContent = "✅ Receipt scanned!";
          return fetch("/add", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ name: extracted_text, type: "food", purchase_date: new Date().toISOString().split("T")[0] })
          });
        })
        .then(() => location.reload());
    };
  
    // 4) Get recipe suggestions
    window.suggestRecipe = () => {
      const ingredients = Array.from(recipeSelect.selectedOptions).map(o => o.value);
      if (!ingredients.length) {
        recipeResult.textContent = "⚠ Please select ingredients!";
        return;
      }
      fetch("/recipes", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ingredients })
      })
      .then(res => res.json())
      .then(({ suggestions }) => {
        recipeResult.textContent = suggestions.length
  ? `🍽 Try: ${suggestions.join(", ")}`
  : "❌ No recipes found.";

      });
    };
  
    // Helper to add a row to the table
    function addRow(item) {
      const tr = document.createElement("tr");
      tr.innerHTML = `
        <td>${item.name}</td>
        <td>${item.purchase_date}</td>
        <td>${item.expiry_date}</td>
        <td class="${getStatusClass(item.expiry_date)}">${getStatusText(item.expiry_date)}</td>
        <td><button class="delete">🗑</button></td>
      `;
      tr.querySelector(".delete").addEventListener("click", () => tr.remove());
      foodList.appendChild(tr);
    }
  
    function getStatusClass(expiry) {
      const diff = (new Date(expiry) - new Date())/(1000*60*60*24);
      return diff < 0 ? "expired" : diff <= 3 ? "expiring-soon" : "";
    }
    function getStatusText(expiry) {
      const diff = (new Date(expiry) - new Date())/(1000*60*60*24);
      return diff < 0 ? "Expired!" : diff <= 3 ? "Expiring Soon!" : "Fresh";
    }
  });