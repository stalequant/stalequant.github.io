var buying = true

function setOperation(op, button) {
    buying = op  === "buying";
    console.log('Operation set to:', op);
    button.parentNode.querySelectorAll('button').forEach(btn => btn.classList.remove('selected'));
    button.classList.add('selected');
}

function cancelOperation(operationId) {
    console.log('Canceling operation:', operationId);
    // Add logic to cancel the specific operation
}

function cancelAllOperations() {
    console.log('Canceling all operations');
    // Add logic to cancel all operations
}

const timeInterval = document.getElementById('timeInterval');
const timeIntervalValue = document.getElementById('timeIntervalValue');

function logSlider(position) {
    // position will be between 0 and 100
    const minp = 0;
    const maxp = 100;

    // The result should be between 1 minute and 1 day (in minutes)
    const minv = Math.log(10);
    const maxv = Math.log(1440*7);

    // calculate adjustment factor
    const scale = (maxv - minv) / (maxp - minp);

    return Math.exp(minv + scale * (position - minp));
}

function formatTime(minutes) {
    if (minutes < 60) {
        return Math.round(minutes) + ' minutes';
    } else if (minutes < 1440) {
        return (minutes / 60).toFixed(1) + ' hours';
    } else {              
        return (minutes / 60/24).toFixed(1) + ' days';
    }
}

timeInterval.addEventListener('input', function() {
    const logValue = logSlider(this.value);
    timeIntervalValue.textContent = formatTime(logValue);
});

// Initialize the slider value
timeInterval.value = 60;
timeInterval.dispatchEvent(new Event('input'));

$(document).ready(function() {
    $('#coinInput').val(coinParam);
    
    $('#coinInput').autocomplete({
        source: coins,
        select: function(event, ui) {
            window.location.href = '?coin=' + ui.item.value;
        }
    });
});