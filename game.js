const map = L.map('map', { zoomControl: false }).setView([60.2, 24.9], 5);
L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors'
}).addTo(map); // map initialization.
const markersGroup = L.layerGroup().addTo(map);

let playerName = "";


function nextStep() {
    document.getElementById('welcome-screen').classList.add('hidden');
    document.getElementById('name-screen').classList.remove('hidden');
}

async function finishSetup() {
    playerName = document.getElementById('player-name-input').value;
    if (!playerName) return alert("Captain, we need your name!");

    try {
        const response = await fetch('http://127.0.0.1:5000/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: playerName })
        });
        document.getElementById('name-screen').classList.add('hidden');
        const briefing = document.getElementById('briefing-screen');
        briefing.querySelector('h1').innerText = `Welcome, Captain ${playerName}!`;
        briefing.querySelector('.goal-text').innerHTML =
            `Budget : Fuel - 800 units and Money - 1000€ <br><br>Mission: Reach 3000€ before turns run out.`;
        briefing.classList.remove('hidden');
    } catch (e) {
        alert("Server connection failed.");
    }
}

function enterGame() {
    document.body.classList.remove('pre-game');
    document.getElementById('setup-overlay').classList.add('hidden');
    updateStatus();
}


async function updateStatus() {
    try {
        const response = await fetch('http://127.0.0.1:5000/status');
        const data = await response.json();

        // 1. Check Win/Loss Conditions
        if (data.money >= data.goal_money) {
            alert(`VICTORY! You reached the goal of ${data.money}€ and won the game!`);
            location.reload();
            return;
        }
        if (data.turns <= 0) {
            alert(`GAME OVER! You ran out of turns. Final money: ${data.money}€. Try again!!`);
            location.reload();
            return;
        }

        // 2. Update HUD Text & Bars
        document.getElementById('money-val').innerText = data.money;
        document.getElementById('fuel-val').innerText = data.fuel;
        document.getElementById('turn-val').innerText = data.turns;

        document.getElementById('fuel-bar').style.width = (data.fuel / data.max_fuel * 100) + "%";
        document.getElementById('money-bar').style.width = (data.money / data.goal_money * 100) + "%";
        document.getElementById('turn-bar').style.width = (data.turns / 15 * 100) + "%";

        // 3. Update Map
        markersGroup.clearLayers();
        const lat = parseFloat(data.coords.lat);
        const lng = parseFloat(data.coords.lng);

        L.circle([lat, lng], {
            color: 'red',
            fillColor: 'red',
            fillOpacity: 1,
            radius: 30000 // Size in meters
        }).addTo(markersGroup).bindPopup(`<b>Location:</b> ${data.city}<br><br><b>Fuel Price:</b> ${data.fuel_price}`);

        map.flyTo([lat, lng], 4);

        renderContracts(data.contracts); // Updates Contracts using renderContracts which is written below.
        console.log(data.contracts);

    } catch (e) {
        console.error("Status update failed:", e);
    }
}

function renderContracts(contracts) {
    const list = document.getElementById('contract-list');
    if (!list) return;
    list.innerHTML = "";

    contracts.forEach(c => {
        const lat = parseFloat(c.lat);
        const lng = parseFloat(c.lng);

        if (!isNaN(lat) && !isNaN(lng)) {
            const contractData = encodeURIComponent(JSON.stringify(c));

            // Generate content for the Map Popup
            const popupContent = `
                <div style="color: #333; min-width: 140px;">
                    <b style="font-size: 1.1em;">${c.destination_name}</b><br>
                    <hr style="margin: 5px 0; border: 0; border-top: 1px solid #eee;">
                    Distance: ${c.distance} km<br>
                    Fuel Req: ${c.fuel_needed} L<br>
                    Reward: ${c.reward} €<br>
                    <button class="btn-action" onclick="fly('${contractData}')" 
                        style="background: #2ecc71; color: black; font-weight: bold; margin-top: 8px;">
                        FLY HERE
                    </button>
                </div>
            `;

            L.circle([lat, lng], {
                color: '#006400',
                fillColor: '#006400',
                fillOpacity: 1,
                radius: 30000
            }).addTo(markersGroup).bindPopup(popupContent);
        }

    });
}

async function fly(encodedContract) {
    const contract = JSON.parse(decodeURIComponent(encodedContract));
    try {
        const response = await fetch('http://127.0.0.1:5000/fly', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ contract: contract })
        });
        const result = await response.json();
        if (result.success) {
            updateStatus();
        } else {
            alert(result.message);
        }
    } catch (e) {
        alert("Flight system failure!");
    }
}


uiRefreshStatus = () => updateStatus();

uiRefreshContracts = async () => {
    const response = await fetch('http://127.0.0.1:5000/refresh', { method: 'POST' });
    const result = await response.json();
    alert(result.message);
    updateStatus();
};

uiRefuel = async () => {
    const amount = prompt("How many units of fuel do you want to buy?");
    if (!amount || isNaN(amount)) return alert('invalid input');
    const response = await fetch('http://127.0.0.1:5000/refuel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: parseInt(amount) })
    });
    const result = await response.json();
    alert(result.message);
    updateStatus(); // I would love to ensure that the contracts didn't change when I refueled.
};