$(function() {
    var socket = io.connect(
        window.location.protocol + '//' + document.domain + ':' +
        window.location.port + '/analysis');

    socket.on('connect', function() {
        var analysis_id = window.location.pathname.split('/')[4];

        socket.emit('subscribe', {'id': +analysis_id});
        socket.on('progress', function(data) {
            if ('sessions' in data) {
                $('#sessionProgress')
                    .width(data.sessions + '%')
                    .attr('aria-valuenow', data.sessions);
            }

            if ('sampling' in data) {
                $('#samplingProgress')
                    .width(data.sampling + '%')
                    .attr('aria-valuenow', data.sampling);
            }
        });
    });

    var maxProb = 0.0;
    for (var role_id in roles) {
        maxProb = Math.max(
            roles[role_id].reduce(function(prev, curr) {
                return prev > curr ? prev : curr;
            }),
            maxProb);
    }

    var barChart = BarChart()
                       .width(960)
                       .x(function(d) {
                           return d;
                       })
                       .y(function(d, i) {
                           return action_types[i + 1];
                       })
                       .margin({top: 30, bottom: 30, right: 30, left: 150})
                       .extent([0, maxProb]);

    for (var role_id in roles) {
        var chartsvg = d3.select('#roleChart' + role_id);
        chartsvg.datum(roles[role_id]).call(barChart);
    }

    $('[data-toggle="tooltip"]').tooltip();
});
