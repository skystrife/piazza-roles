$(function() {
    var socket = io.connect(window.location.protocol + '//' + document.domain
                            + ':' + window.location.port + '/network');

    socket.on('connect', function() {
        var network_id = window.location.pathname.split('/')[2];

        socket.emit('subscribe', {'id': +network_id});
        socket.on('progress', function(data) {
            var bar = $('#crawlProgress')
                .width(data.progress + '%')
                .attr('aria-valuenow', data.progress);
            if (data.progress >= 100)
                bar.addClass('bg-success');
        });

        socket.on('finished', function() {
            $('#viewClassButton').removeClass('invisible');
        });
    });
});
