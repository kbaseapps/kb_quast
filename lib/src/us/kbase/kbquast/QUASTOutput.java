
package us.kbase.kbquast;

import java.util.HashMap;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: QUASTOutput</p>
 * <pre>
 * Ouput of the run_quast function.
 * shock_node - the id of the shock node where the zipped QUAST output is stored.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "shock_node"
})
public class QUASTOutput {

    @JsonProperty("shock_node")
    private String shockNode;
    private Map<String, Object> additionalProperties = new HashMap<String, Object>();

    @JsonProperty("shock_node")
    public String getShockNode() {
        return shockNode;
    }

    @JsonProperty("shock_node")
    public void setShockNode(String shockNode) {
        this.shockNode = shockNode;
    }

    public QUASTOutput withShockNode(String shockNode) {
        this.shockNode = shockNode;
        return this;
    }

    @JsonAnyGetter
    public Map<String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public String toString() {
        return ((((("QUASTOutput"+" [shockNode=")+ shockNode)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
