$(function() {
    var barChart = BarChart()
                       .width(960)
                       .x(function(d) {
                           return d;
                       })
                       .y(function(d, i) {
                           return {'name': `Role ${i + 1}`, 'description': ''};
                       })
                       .margin({top: 30, bottom: 30, right: 30, left: 150});

    d3.select('#proportionChart').datum(proportions).call(barChart);

    $('[data-toggle="tooltip"]').tooltip();
});
