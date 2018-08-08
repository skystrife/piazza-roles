$(function() {
    var barChart = BarChart()
                       .width(960)
                       .x(function(d) {
                           return d;
                       })
                       .y(function(d, i) {
                           return action_types[i + 1];
                       })
                       .margin({top: 30, bottom: 30, right: 30, left: 150});

    d3.select('#roleChart').datum(role).call(barChart);

    $('[data-toggle="tooltip"]').tooltip();

    $('[data-toggle="datatable"]').DataTable();
});
