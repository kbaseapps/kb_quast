
package us.kbase.kbquast;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import javax.annotation.Generated;
import com.fasterxml.jackson.annotation.JsonAnyGetter;
import com.fasterxml.jackson.annotation.JsonAnySetter;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.annotation.JsonPropertyOrder;


/**
 * <p>Original spec-file type: QUASTParams</p>
 * <pre>
 * Input for running QUAST.
 * assemblies - the list of assemblies upon which QUAST will be run.
 * -OR-
 * files - the list of FASTA files upon which QUAST will be run.
 * </pre>
 * 
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
@Generated("com.googlecode.jsonschema2pojo")
@JsonPropertyOrder({
    "assemblies",
    "files"
})
public class QUASTParams {

    @JsonProperty("assemblies")
    private List<String> assemblies;
    @JsonProperty("files")
    private List<FASTAFile> files;
    private Map<java.lang.String, Object> additionalProperties = new HashMap<java.lang.String, Object>();

    @JsonProperty("assemblies")
    public List<String> getAssemblies() {
        return assemblies;
    }

    @JsonProperty("assemblies")
    public void setAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
    }

    public QUASTParams withAssemblies(List<String> assemblies) {
        this.assemblies = assemblies;
        return this;
    }

    @JsonProperty("files")
    public List<FASTAFile> getFiles() {
        return files;
    }

    @JsonProperty("files")
    public void setFiles(List<FASTAFile> files) {
        this.files = files;
    }

    public QUASTParams withFiles(List<FASTAFile> files) {
        this.files = files;
        return this;
    }

    @JsonAnyGetter
    public Map<java.lang.String, Object> getAdditionalProperties() {
        return this.additionalProperties;
    }

    @JsonAnySetter
    public void setAdditionalProperties(java.lang.String name, Object value) {
        this.additionalProperties.put(name, value);
    }

    @Override
    public java.lang.String toString() {
        return ((((((("QUASTParams"+" [assemblies=")+ assemblies)+", files=")+ files)+", additionalProperties=")+ additionalProperties)+"]");
    }

}
