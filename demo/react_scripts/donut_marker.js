import React from 'react';
import {RadialChart, Hint} from 'react-vis';

const OK_COLOR = "green";
const WARNING_COLOR = "yellow";
const ERROR_COLOR = "red";
const BACKGROUND_COLOR = "black";
const TEXT_COLOR = "white";

class DonutChart extends React.Component {
    state = {
        value: false
    };

    constructor(props) {
        super(props);
    }

    render() {
        const {value} = this.state;
        return (
            <div style={{display: "flex", alignItems: "left", justifyContent: "left"}}>
            <div
                style={{
                    display: "flex", 
                    alignItems: "center",
                    justifyContent: "center"
                }}
            >
                <RadialChart
                    className={"donut-chart"}
                    radius={this.props.radius}
                    innerRadius={this.props.innerRadius}
                    getAngle={d => d.theta}
                    colorType={"literal"}
                    data={[
                        {
                            theta: this.props.okValue,
                            className: "ok",
                            color: OK_COLOR
                        },
                        {
                            theta: this.props.warningValue,
                            className: "warning",
                            color: WARNING_COLOR
                        },
                        {
                            theta: this.props.errorValue,
                            className: "error",
                            color: ERROR_COLOR
                        }
                    ]}
                    width={2 * this.props.radius + 10}
                    height={2 * this.props.radius + 10}
                    margin={{left: 0, right: 0, top: 0, bottom: 0}}
                    padAngle={0.00}
                >
                    {value !== false && <Hint value={value} />}
                </RadialChart>
                <div 
                    style={{
                        display: "flex", 
                        alignItems: "center",
                        justifyContent: "center",
                        position: "absolute",
                        backgroundColor: BACKGROUND_COLOR,
                        borderRadius: "50%",
                        width: 2 * this.props.innerRadius,
                        height: 2 * this.props.innerRadius
                    }}
                >
                    <div 
                        style={{
                            position: "absolute"
                        }}
                    >
                        <strong
                            style={{
                                "textAlign": "center",
                                color: TEXT_COLOR,
                                "fontSize": (0.8 * this.props.innerRadius).toString() + "px"
                            }}
                        >
                            {(this.props.okValue + this.props.warningValue + this.props.errorValue).toString()}
                        </strong>
                        <br/>
                        <div
                            style={{
                                "textAlign": "center",
                                color: TEXT_COLOR,
                                "fontSize": (0.4 * this.props.innerRadius).toString() + "px"
                            }}
                        >
                            {"\n" + this.props.extraText}
                        </div>
                    </div>
                </div>
            </div>
            </div>
        );
    }
}

export default DonutChart;
