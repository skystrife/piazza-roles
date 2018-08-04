function BarChart() {
    var width = 960, height = 500, xValue = function(d) {
        return d[0];
    }, yValue = function(d) {
        return d[1];
    }, extent = null;

    var margin = {top: 30, right: 30, bottom: 30, left: 30},
        xScale = d3.scaleLinear(), yScale = d3.scaleBand(),
        xAxis = d3.axisBottom(), yAxis = d3.axisLeft(), colorScale;

    function chart(selection) {
        selection.each(function(data) {
            // Convert to standard data representation greedily;
            // this is needed for nondeterministic accessors.
            data = data.map(function(d, i) {
                return [xValue.call(data, d, i), yValue.call(data, d, i)];
            });

            var g = d3.select(this).append('g').attr(
                'transform',
                'translate(' + margin.left + ',' + margin.top + ')');

            extent = extent || d3.extent(data, function(d) {
                return d[0];
            });
            extent[0] = Math.min(0, extent[0]);
            xScale.range([0, width - margin.left - margin.right])
                .domain(extent);

            yScale.range([0, height - margin.top - margin.bottom])
                .padding(.1)
                .domain(data.map(function(d) {
                    return d[1].name;
                }));
            colorScale = d3.scaleSequential(d3.interpolateMagma).domain([
                -0.2 * data.length, 1.2 * data.length
            ]);

            var xAxis = d3.axisBottom(xScale).tickFormat(d3.format('.0%'));

            var yAxis = d3.axisLeft(yScale);

            g.selectAll('.bar')
                .data(data)
                .enter()
                .append('rect')
                .attr('class', 'bar')
                .attr(
                    'x',
                    function(d) {
                        return (xScale(0) - xScale(d[0])) > 0 ? xScale(d[0]) :
                                                                xScale(0);
                    })
                .attr(
                    'y',
                    function(d) {
                        return yScale(d[1].name);
                    })
                .attr('height', yScale.bandwidth())
                .attr(
                    'width',
                    function(d) {
                        return Math.abs(xScale(0) - xScale(d[0]));
                    })
                .attr(
                    'fill',
                    function(d, i) {
                        return colorScale(i);
                    })
                .attr('data-toggle', 'tooltip')
                .attr('data-placement', 'top')
                .attr('title', function(d) {
                    return d3.format('.1%')(d[0])
                });

            g.append('g')
                .attr('class', 'x axis')
                .attr('transform', 'translate(0,' + yScale.range()[1] + ')')
                .call(xAxis);

            g.append('g').attr('class', 'y axis').call(yAxis);

            g.selectAll('.y.axis > .tick')
                .attr('data-toggle', 'tooltip')
                .attr('data-placement', 'left')
                .attr('title', function(d, i) {
                    return action_types[i + 1].description;
                });


            g.append('path')
                .datum([
                    [d3.min(xScale.range()), yScale(0)],
                    [d3.max(xScale.range()), yScale(0)]
                ])
                .attr('d', d3.line())
                .style('stroke', '#333')
                .style('stroke-width', '1')
        });
    }

    chart.margin = function(_) {
        if (!arguments.length) return margin;
        margin = _;
        return chart;
    };

    chart.width = function(_) {
        if (!arguments.length) return width;
        width = _;
        return chart;
    };

    chart.height = function(_) {
        if (!arguments.length) return height;
        height = _;
        return chart;
    };

    chart.x = function(_) {
        if (!arguments.length) return xValue;
        xValue = _;
        return chart;
    };

    chart.y = function(_) {
        if (!arguments.length) return yValue;
        yValue = _;
        return chart;
    };

    chart.xScale = function(_) {
        if (!arguments.length) return xScale;
        xScale = _;
        return chart;
    };

    chart.yScale = function(_) {
        if (!arguments.length) return yScale;
        yScale = _;
        return chart;
    };

    chart.extent = function(_) {
        if (!arguments.length) return extent;
        extent = _;
        return chart;
    };

    return chart;
}


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

    var numActions = Object.keys(action_types).length;
    var barHeight = 20;

    var barChart = BarChart()
                       .width(960)
                       .height(barHeight * numActions)
                       .x(function(d) {
                           return d;
                       })
                       .y(function(d, i) {
                           return action_types[i + 1];
                       })
                       .margin({top: 30, bottom: 30, right: 30, left: 150})
                       .extent([0, 0.6]);

    for (var role_id in roles) {
        var chartsvg = d3.select('#roleChart' + role_id);
        chartsvg.attr('width', 960).attr('height', barHeight * numActions);
        chartsvg.attr('preserveAspectRatio', 'xMinYMin meet')
            .attr('viewBox', '0 0 960 ' + (barHeight * numActions))
        chartsvg.datum(roles[role_id]).call(barChart);
    }

    $('[data-toggle="tooltip"]').tooltip();
});
