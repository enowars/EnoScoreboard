$(document).ready(function () {
    loadScoreboard();
});



function escapeHtml(a) {
    return a+""
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function getLostDefenseString(points) {
    if (points > 0)
        return "-"+points;
    else
        return 0;
}

var statusMap = [
    "CheckerError",
    "Ok",
    "Recovering",
    "Mumble",
    "Down"
]

function getServiceStatusString(i) {
    return statusMap[i];
}

function loadScoreboard() {
    console.log("loadScoreboard()");
    $.get({url: "scoreboard.json", cache: false}, function( data ) {
        var teams = data["Teams"];
        var services = data["Services"];
        var currentRound = data["CurrentRound"];

        // build table
        var container = $("#scoreboard-container");
        var table = $('<table id="scoreboard-table"></table>');
        var round_display = $("#round_display")[0];
        round_display.innerHTML = `Next round: ${escapeHtml(currentRound)}`;
        container.append(table);

        var header = `<tr>
        <th></th>
        <th class="rightborder">Team</th>
        `;
        for (var serviceId in services) {
            var service = services[serviceId];
            header += `
            <th>${escapeHtml(service["Name"])}</th>
            `;
        }

        header += `
        <th class="leftborder">Total</th>
        </tr>`;
        table.append($(header));

        // fill table
        var i = 1;
        teams.forEach(function(team) {
            var row = `<tr class="topborder">
            <td class="bolt">${i}.</td>
            <td class="rightborder"><div>
                <div>${escapeHtml(team["Name"])}</div>
                <div>Id: ${escapeHtml(team["TeamId"])}</div>
            </div></td>`;
            for (var serviceId in services) {
                var serviceDetails = team["ServiceDetails"][serviceId];
                service_status_class = getServiceStatusString(serviceDetails["ServiceStatus"]);
                row += `<td class="${service_status_class}"><div>
                <div><span class="glyphicon glyphicon-fire"></span> ${escapeHtml(serviceDetails["AttackPoints"])}</div>
                <div><span class="glyphicon glyphicon-tower"></span> ${escapeHtml(getLostDefenseString(serviceDetails["LostDefensePoints"]))}</div>
                <div><span class="glyphicon glyphicon-dashboard"></span> ${escapeHtml(serviceDetails["ServiceLevelAgreementPoints"])}</div>
                <div>${service_status_class}</div>
                </div></td>`;
            }
            row += `
            <td class="leftborder">
                <div><span class="glyphicon glyphicon-fire"></span> ${escapeHtml(team["AttackPoints"])}</div>
                <div><span class="glyphicon glyphicon-tower"></span> ${escapeHtml(getLostDefenseString(team["LostDefensePoints"]))}</div>
                <div><span class="glyphicon glyphicon-dashboard"></span> ${escapeHtml(team["ServiceLevelAgreementPoints"])}</div>
                <div class="bolt"><span class="icon">Σ</span> ${escapeHtml(team["TotalPoints"])}</div>
            </td></tr>`
            table.append($(row));
            i++;
        });
    });    
}
