$(function() {
    var socket = io.connect(window.location.protocol + '//' + document.domain
                            + ':' + window.location.port + '/analysis');

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
});
