// Copyright 2020 Tampere University
// This software was developed as a part of the CityIoT project: https://www.cityiot.fi/english
// This source code is licensed under the 3-clause BSD license. See license.txt in the repository root directory.
// Author(s): Ville Heikkilä <ville.heikkila@tuni.fi>
class StreetlightEnergy extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        return (
            <reactVis.XYPlot
                width={800}
                height={300}>
                <reactVis.VerticalBarSeries
					colorRange={["red", "blue"]}
                    barWidth={1.0}
                    data={this.props.data}/>
                <reactVis.HorizontalGridLines/>
                <reactVis.XAxis title="Hour in local time"/>
                <reactVis.YAxis title="Estimated hourly energy consumption (Wh)"/>
            </reactVis.XYPlot>
        );
    }
}

function renderEnergyGraph(targetTag, data) {
    ReactDOM.render(
        <StreetlightEnergy data={data} />,
        document.getElementById(targetTag)
    )
}
